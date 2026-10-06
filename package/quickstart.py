#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Nurymanau
"""Single text request through pinned WARP on macOS/Apple Silicon."""
import argparse
from dataclasses import replace
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
GIB = 1024**3

def options():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('prompt', nargs='?', default='Reply exactly: OK')
    p.add_argument('--warp', type=Path, default=ROOT/'warp')
    p.add_argument('--model', type=Path, default=ROOT/'glm53-vq3r.waste')
    p.add_argument('--max-tokens', type=int, default=128)
    p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--check', action='store_true', help='Check installation without loading weights')
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    a = p.parse_args()
    a.warp = a.warp.resolve(); a.model = a.model.resolve()
    if not 1 <= a.max_tokens <= 768 or not 60 <= a.timeout <= 3600:
        p.error('Require 1..768 output tokens and 60..3600 seconds')
    if not a.prompt.strip(): p.error('Prompt must not be empty')
    return a

def check(a):
    if sys.platform != 'darwin': raise RuntimeError('This helper is tested on macOS only')
    for name, expected in json.loads((ROOT/'runtime-source-sha256.json').read_text()).items():
        if hashlib.sha256((a.warp/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('WARP source differs from the pinned release: '+name)
    if not (a.warp/'libwaste.dylib').is_file(): raise RuntimeError('Build WARP first: make -j2')
    for row in json.loads((ROOT/'weights-manifest.json').read_text()):
        p = a.model/Path(row['path']).name
        if p.stat().st_size != row['size']: raise RuntimeError('Wrong file size: '+str(p))

def worker(a):
    sys.path.insert(0, str(a.warp))
    from serve.engine import Engine
    from serve.chatfmt import ChatFormat, PlainParser
    from serve import glmtools
    started = time.monotonic()
    engine = Engine(str(a.model), ram_budget_bytes=6*GIB, ctx_tokens=1536,
                    n_threads=4, cache_policy=0, verify_records=True, exclusive_open=True)
    try:
        fmt = replace(ChatFormat.load(engine), effort='<|system|>Reasoning Effort: {}')
        tokens = engine.tokenize_segments(fmt.build_chat_segments(
            [{'role':'user','content':a.prompt}], thinking_effort='low'))
        if len(tokens)+a.max_tokens > 1536:
            raise ValueError('Input plus output reserve exceeds 1536 tokens; shorten the prompt')
        parser = PlainParser(markers={fmt.stop_id:fmt.stop_marker, **fmt.tool_markers},
                             think_close_id=fmt.think_close_id, in_think=True,
                             tool_parser=glmtools.ToolParser())
        count=0; decode_ms=0.; first_visible=None
        print(f'Processing {len(tokens)} input tokens; prefill can take minutes.', file=sys.stderr, flush=True)
        def callback(tid, piece, info):
            nonlocal count, decode_ms, first_visible
            count += 1; decode_ms += float(info.ms_total)
            delta = parser.feed_token(tid, piece)
            if delta.content:
                if first_visible is None: first_visible=time.monotonic()-started
                print(delta.content, end='', flush=True)
            return not parser.finished
        engine.generate(tokens, callback, temperature=0, seed=42,
                        max_tokens=a.max_tokens, stop_tokens=[fmt.stop_id])
        parser.finish(); print(flush=True)
        complete=bool(parser.finished and parser.content and not parser.tool_calls)
        print(json.dumps({'complete':complete, 'input_tokens':len(tokens), 'generated_tokens':count,
              'first_visible_s_including_load':first_visible, 'wall_s':time.monotonic()-started,
              'decode_tok_s':count/(decode_ms/1000) if decode_ms else None}), file=sys.stderr, flush=True)
        return 0 if complete else 2
    finally:
        engine.close()

def swap_bytes():
    text=subprocess.check_output(['/usr/sbin/sysctl','-n','vm.swapusage'],text=True)
    match=re.search(r'used\s*=\s*([0-9.]+)([KMG])', text)
    if not match: raise RuntimeError('Cannot measure system swap')
    return float(match[1])*{'K':1024,'M':1024**2,'G':GIB}[match[2]]

def supervise(a):
    with (ROOT/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        env={k:v for k,v in os.environ.items() if not k.startswith('WASTE_')}
        env.update(WASTE_LIB=str(a.warp/'libwaste.dylib'), WASTE_IO_THREADS='2',
                   WASTE_IO_DEPTH='2', WASTE_LOOKAHEAD='6', WASTE_METAL_MOE='0',
                   WASTE_PROFILE='0', OMP_NUM_THREADS='4', PYTHONUNBUFFERED='1')
        baseline=swap_bytes(); started=time.monotonic(); peak=0; growth_peak=0
        command=[sys.executable,str(Path(__file__).resolve()),'--worker','--warp',str(a.warp),
                 '--model',str(a.model),'--max-tokens',str(a.max_tokens),'--timeout',str(a.timeout),'--',a.prompt]
        child=subprocess.Popen(command,env=env,start_new_session=True)
        try:
            while child.poll() is None:
                lines=subprocess.check_output(['/bin/ps','-axo','pgid=,rss='],text=True).splitlines()
                rss=sum(int(parts[1])*1024 for line in lines if len(parts:=line.split())==2 and int(parts[0])==child.pid)
                growth=max(0,swap_bytes()-baseline);peak=max(peak,rss);growth_peak=max(growth_peak,growth)
                if rss>9*GIB or growth>512*1024**2: raise RuntimeError('Memory/swap limit exceeded')
                if time.monotonic()-started>a.timeout: raise TimeoutError('Request timeout')
                time.sleep(1)
            return child.returncode
        finally:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL);child.wait()
            print(json.dumps({'peak_rss_bytes':peak,'peak_swap_growth_bytes':growth_peak}),file=sys.stderr)

def main():
    a=options();check(a)
    if a.check:
        print('Installation and file sizes OK; run verify.py for full SHA256 verification.')
        return 0
    return worker(a) if a.worker else supervise(a)

if __name__=='__main__':
    try:sys.exit(main())
    except KeyboardInterrupt:sys.exit(130)
    except Exception as error:
        print(str(error),file=sys.stderr);sys.exit(1)
