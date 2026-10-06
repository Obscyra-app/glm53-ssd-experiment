# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Nurymanau
"""Run pinned WARP with byte-equivalent row-chunked trunk Q8 quantization."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'warp/tools'))
import torch
import convert
original_q8=convert.quantize_q8g

def bounded_q8(W,group=128):
    shape=list(W.shape);rows=W.reshape(-1,shape[-1]);padded=((shape[-1]+group-1)//group)*group
    q=torch.empty((rows.shape[0]*padded,),dtype=torch.int8)
    sc=torch.empty((rows.shape[0]*(padded//group),),dtype=torch.float16)
    for start in range(0,rows.shape[0],256):
        end=min(rows.shape[0],start+256)
        block,scales,_=original_q8(rows[start:end],group)
        q[start*padded:end*padded]=block
        sc[start*(padded//group):end*(padded//group)]=scales
    return q,sc,shape


def stream_q8(st,name,tf,out_name):
    shape=list(st.shape(name));assert len(shape)==2
    hdr,_=st._header(st.wm[name]);assert hdr[name]['dtype'] in ('BF16','F16','F32')
    off=tf.tell();scales=[]
    for start in range(0,shape[0],256):
        t=st.row_slice(name,start,min(shape[0],start+256)).float()
        q,sc,_=original_q8(t)
        tf.write(convert.raw_bytes(q));scales.append(sc)
    sc_off=tf.tell()
    for sc in scales:tf.write(convert.raw_bytes(sc))
    print('streamed trunk Q8',name,shape,flush=True)
    return {'name':out_name,'fmt':convert.FMT_Q8G,'off':off,'shape':shape,'group':128,'scale_off':sc_off,'bytes':tf.tell()-off}

def install_streaming_trunk():
    import inspect
    original=convert.build_trunk
    source=inspect.getsource(original)
    needle='                t = st.tensor(name)\n'
    assert source.count(needle)==1
    insertion="""                if name.endswith(('embed_tokens.weight','lm_head.weight')):
                    out_name = trunk_rename(rename(name) if rename else name, _trunk_seg)
                    tindex.append(_stream_q8(st, name, tf, out_name))
                    continue
"""
    convert._stream_q8=stream_q8
    exec(compile(source.replace(needle,insertion+needle),__file__,'exec'),convert.__dict__)
    return original

def self_test():
    import tempfile,json
    from types import SimpleNamespace
    from safetensors.torch import save_file
    torch.manual_seed(17)
    for shape in [(2048,1024),(333,257),(2,33,257),(1,128)]:
        w=torch.randn(shape);a=original_q8(w);b=bounded_q8(w)
        assert a[2]==b[2] and torch.equal(a[0],b[0]) and torch.equal(a[1],b[1]),shape
        print('Q8 row-chunk byte equivalence PASS',shape)
    original=install_streaming_trunk()
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);src=root/'src';src.mkdir()
        tensors={n:torch.randn(shape).bfloat16() for n,shape in [('lm_head.weight',(777,257)),('model.language_model.embed_tokens.weight',(515,384)),('model.language_model.norm.weight',(384,))]}
        save_file(tensors,str(src/'part.safetensors'))
        (src/'model.safetensors.index.json').write_text(json.dumps({'weight_map':{k:'part.safetensors' for k in tensors}}))
        results=[]
        for i,fn in enumerate([original,convert.build_trunk]):
            out=root/str(i);out.mkdir();st=convert.ST(str(src));sr=convert.ShardReader(str(src))
            if i:
                orig_tensor=st.tensor
                def no_full_read(name):
                    if name.endswith(('embed_tokens.weight','lm_head.weight')):raise AssertionError('whole matrix read')
                    return orig_tensor(name)
                st.tensor=no_full_read
            args=SimpleNamespace(out=str(out),skip_trunk=False,trunk8=False,trunk_bits=4)
            index=fn(args,sr,st,None,str(out/'manifest.json'))
            results.append((index,(out/'trunk.bin.tmp').read_bytes()))
        assert results[0]==results[1]
        print('Full trunk byte/index equivalence PASS; padded BF16 rows; whole embedding reads forbidden')

if __name__=='__main__':
    if sys.argv[1:]==['--self-test']:self_test()
    else:
        install_streaming_trunk()
        convert.quantize_q8g=bounded_q8
        sys.exit(convert.main())
