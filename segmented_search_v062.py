import argparse
import csv
import heapq
import json
import os
import shutil
import struct
from collections import defaultdict, OrderedDict
from fractions import Fraction
from itertools import combinations
from math import gcd, isqrt
from pathlib import Path
from time import perf_counter

VERSION = '0.6.2'
PAIR = struct.Struct('<QQ')
FIELDS = ['a','b','c','x','y','z','space_squared','space_floor','square_gap','normalized_gap','perfect']


def is_square(n):
    r = isqrt(n)
    return r*r == n


def gap_score(n):
    r = isqrt(n)
    k = r if n-r*r <= (r+1)*(r+1)-n else r+1
    return abs(n-k*k), Fraction(abs(n-k*k), r+k)


def pairs(bound):
    m = 2
    while 2*m*m < 3*bound:
        for n in range(1, min(m-1, bound//(2*m))+1):
            if gcd(m,n) != 1 or (m-n)%2 == 0:
                continue
            a,b = sorted((m*m-n*n,2*m*n))
            if b > bound:
                continue
            for k in range(1,bound//b+1):
                yield k*a,k*b
        m += 1


class BoundedWriter:
    def __init__(self, memory_limit_mb, open_files=32):
        self.limit = memory_limit_mb*1024*1024
        self.handles = OrderedDict()
        self.buffers = {}
        self.bytes_pending = 0
        self.open_files = open_files
        self.flushes = 0

    def _handle(self, path):
        if path in self.handles:
            h = self.handles.pop(path)
        else:
            if len(self.handles) >= self.open_files:
                _, old = self.handles.popitem(last=False)
                old.close()
            h = open(path,'ab',buffering=1024*1024)
        self.handles[path] = h
        return h

    def _flush(self, path):
        data = self.buffers.pop(path, None)
        if data:
            self._handle(path).write(data)
            self.bytes_pending -= len(data)
            self.flushes += 1

    def write(self, path, record):
        buf = self.buffers.get(path)
        if buf is None:
            buf = bytearray()
            self.buffers[path] = buf
        buf.extend(record)
        self.bytes_pending += len(record)
        if self.bytes_pending >= self.limit:
            # Flush the largest buffer to minimize the number of disk writes.
            biggest = max(self.buffers, key=lambda p: len(self.buffers[p]))
            self._flush(biggest)

    def close(self):
        for path in list(self.buffers):
            self._flush(path)
        for h in self.handles.values():
            h.close()
        self.handles.clear()


def save_manifest(path, info):
    tmp = path.with_suffix('.tmp')
    with open(tmp,'w',encoding='utf-8') as f:
        json.dump(info,f,indent=2)
    os.replace(tmp,path)


def prepare(workdir, bound, segment_size, memory_limit):
    workdir.mkdir(parents=True,exist_ok=True)
    manifest = workdir/'manifest.json'
    signature = {'version':VERSION,'bound':bound,'segment_size':segment_size}
    if manifest.exists():
        with open(manifest,encoding='utf-8') as f:
            info = json.load(f)
        if any(info.get(k)!=v for k,v in signature.items()):
            raise RuntimeError('Workspace parameters differ; use a new --workdir')
        if info.get('generation_complete'):
            print('Reusing completed pair files.')
            return info['pair_count'],0.0,True
        raise RuntimeError('Incomplete pair generation: remove workspace and restart')
    if any(workdir.iterdir()):
        raise RuntimeError('Workspace is not empty and has no manifest')
    t = perf_counter()
    writer = BoundedWriter(memory_limit)
    count = 0
    try:
        for a,b in pairs(bound):
            segment = (a-1)//segment_size
            writer.write(workdir/f'pairs_{segment:06d}.bin',PAIR.pack(a,b))
            count += 1
    finally:
        writer.close()
    save_manifest(manifest,{**signature,'generation_complete':True,'pair_count':count})
    elapsed = perf_counter()-t
    print(f'Pythagorean graph edges: {count}')
    print(f'Pair generation: {elapsed:.3f}s; buffer flushes: {writer.flushes}')
    return count,elapsed,False


def process_segment(workdir, sid):
    result = workdir/f'results_{sid:06d}.csv'
    if result.exists():
        return False,0
    path = workdir/f'pairs_{sid:06d}.bin'
    neighbors = defaultdict(list)
    if path.exists():
        with open(path,'rb') as f:
            while chunk := f.read(PAIR.size*8192):
                if len(chunk)%PAIR.size:
                    raise RuntimeError(f'Corrupt pair file: {path}')
                for a,b in PAIR.iter_unpack(chunk):
                    neighbors[a].append(b)
    tmp = result.with_suffix('.tmp')
    count = 0
    with open(tmp,'w',newline='',encoding='utf-8') as f:
        out = csv.writer(f)
        out.writerow(FIELDS)
        for a in sorted(neighbors):
            for b,c in combinations(sorted(set(neighbors[a])),2):
                z2 = b*b+c*c
                if not is_square(z2) or gcd(gcd(a,b),c)!=1:
                    continue
                x2,y2 = a*a+b*b,a*a+c*c
                x,y,z = isqrt(x2),isqrt(y2),isqrt(z2)
                if x*x!=x2 or y*y!=y2 or z*z!=z2:
                    raise AssertionError('Invalid Euler brick')
                s = a*a+b*b+c*c
                d = isqrt(s)
                gap,norm = gap_score(s)
                out.writerow([a,b,c,x,y,z,s,d,gap,f'{float(norm):.12f}',int(d*d==s)])
                count += 1
    os.replace(tmp,result)
    return True,count


def verify_small(bound):
    direct = set()
    for a in range(1,bound+1):
        for b in range(a+1,bound+1):
            if is_square(a*a+b*b):
                direct.add((a,b))
    generated = set(pairs(bound))
    if direct!=generated:
        raise AssertionError(f'Pair verification failed: missing {sorted(direct-generated)[:5]}, extra {sorted(generated-direct)[:5]}')
    graph = defaultdict(set)
    for a,b in generated:
        graph[a].add(b)
        graph[b].add(a)
    bricks = set()
    for a in graph:
        for b in graph[a]:
            if b>a:
                for c in graph[a]:
                    if c>b and c in graph[b] and gcd(gcd(a,b),c)==1:
                        bricks.add((a,b,c))
    print(f'VERIFICATION PASSED: bound={bound}, pairs={len(direct)}, primitive bricks={len(bricks)}')


def read_bricks(path):
    with open(path,newline='',encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not {'a','b','c'}.issubset(reader.fieldnames or []):
            raise ValueError(f'CSV missing a,b,c: {path}')
        return {tuple(int(row[k]) for k in ('a','b','c')) for row in reader}


def consolidate(workdir, count, output, top):
    tmp = output.with_name(output.name+'.tmp')
    heap=[]
    found=perfect=0
    with open(tmp,'w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f)
        writer.writerow(FIELDS)
        for sid in range(count):
            path=workdir/f'results_{sid:06d}.csv'
            if not path.exists():
                raise RuntimeError(f'Missing segment {sid}')
            with open(path,newline='',encoding='utf-8') as inp:
                for row in csv.DictReader(inp):
                    writer.writerow([row[k] for k in FIELDS])
                    a,b,c=(int(row[k]) for k in ('a','b','c'))
                    s=int(row['space_squared'])
                    gap,norm=gap_score(s)
                    found+=1
                    perfect+=int(row['perfect'])
                    key=(-norm,-gap,-a,-b,-c)
                    item=(key,(a,b,c,gap,norm))
                    if len(heap)<top:
                        heapq.heappush(heap,item)
                    elif key>heap[0][0]:
                        heapq.heapreplace(heap,item)
    os.replace(tmp,output)
    return found,perfect,sorted(heap,reverse=True)


def run(args):
    start=perf_counter()
    workdir=Path(args.workdir).resolve()
    output=Path(args.output).resolve()
    if output.is_relative_to(workdir):
        raise ValueError('Output must be outside workspace')
    if args.verify_output and Path(args.verify_output).resolve()==output:
        raise ValueError('Reference CSV must differ from output CSV')
    if args.verify:
        verify_small(args.verify)
    _,generation_time,reused=prepare(workdir,args.max_edge,args.segment_size,args.memory_limit_mb)
    segments=(args.max_edge+args.segment_size-1)//args.segment_size
    t=perf_counter()
    completed=0
    for sid in range(segments):
        fresh,n=process_segment(workdir,sid)
        completed+=int(fresh)
        if (sid+1)%args.progress_every==0 or sid+1==segments:
            print(f'Segments: {sid+1}/{segments}; new: {completed}; last bricks: {n}; elapsed: {perf_counter()-start:.2f}s',flush=True)
    segment_time=perf_counter()-t
    t=perf_counter()
    found,perfect,best=consolidate(workdir,segments,output,args.top)
    consolidation_time=perf_counter()-t
    if args.verify_output:
        actual=read_bricks(output)
        expected=read_bricks(Path(args.verify_output))
        same=actual==expected and len(actual)==found
        print(f'OUTPUT IDENTICAL: {same}; expected={len(expected)}, actual={len(actual)}, rows={found}')
        if not same:
            print('Missing:',sorted(expected-actual)[:10])
            print('Extra:',sorted(actual-expected)[:10])
            raise RuntimeError('Output comparison failed; workspace retained')
    print('\nEULER BRICK RESEARCH - SEGMENTED SEARCH v0.6.2')
    print(f'Max edge: {args.max_edge}; segments: {segments}')
    print(f'Primitive Euler bricks: {found}; Perfect cuboids: {perfect}')
    print(f'Pair generation: {generation_time:.3f}s'+(' (reused)' if reused else ''))
    print(f'Segment processing: {segment_time:.3f}s')
    print(f'Consolidation: {consolidation_time:.3f}s')
    print(f'Total time: {perf_counter()-start:.3f}s')
    print('\nTOP CANDIDATES')
    for _,(a,b,c,gap,norm) in best:
        print(f'({a}, {b}, {c}) gap={gap} normalized={float(norm):.9f}')
    print(f'\nResults: {output}')
    if args.cleanup:
        # Cleanup only after all output checks have succeeded.
        shutil.rmtree(workdir)
        print('Temporary workspace removed after successful completion.')
    else:
        print(f'Workspace retained: {workdir}')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--max-edge',type=int,default=1000)
    p.add_argument('--segment-size',type=int,default=10000)
    p.add_argument('--memory-limit-mb',type=int,default=32)
    p.add_argument('--top',type=int,default=20)
    p.add_argument('--verify',type=int,default=300)
    p.add_argument('--progress-every',type=int,default=10)
    p.add_argument('--workdir',default='work_062')
    p.add_argument('--output',default='bricks_062.csv')
    p.add_argument('--verify-output',default=None)
    p.add_argument('--cleanup',action='store_true')
    args=p.parse_args()
    if args.max_edge<1 or args.max_edge>4_000_000_000 or args.segment_size<1 or args.memory_limit_mb<1 or args.top<1 or args.progress_every<1 or not 0<=args.verify<=1000:
        p.error('Invalid parameters')
    run(args)
