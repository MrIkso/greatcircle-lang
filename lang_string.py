#!/usr/bin/env python3
import argparse, io, struct

u32le = lambda b: struct.unpack('<I', b)[0]
u32be = lambda b: struct.unpack('>I', b)[0]
p32le = lambda x: struct.pack('<I', x & 0xFFFFFFFF)
p32be = lambda x: struct.pack('>I', x & 0xFFFFFFFF)

def fnv1a_32(data: bytes) -> int:
    h = 0x811C9DC5
    for c in data:
        h ^= c
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h

def read_sstring(f: io.BufferedReader) -> bytes:
    sz_b = f.read(4)
    if len(sz_b) != 4: raise EOFError('EOF size')
    sz = u32le(sz_b)
    data = f.read(sz)
    if len(data) != sz: raise EOFError('EOF data')
    nul = f.read(1)
    if len(nul) != 1: raise EOFError('EOF null')
    if nul != b'\x00': raise ValueError('nullByte != 0x00')
    return data

def write_sstring(f: io.BufferedWriter, data: bytes):
    f.write(p32le(len(data)))
    f.write(data)
    f.write(b'\x00')

def export_to_txt(bin_path: str, txt_path: str, strict_hash: bool):
    with open(bin_path, 'rb') as f:
        size_le = u32le(f.read(4))
        count_be = u32be(f.read(4))
        entries = []
        for i in range(count_be):
            h = u32be(f.read(4))
            key_b = read_sstring(f)
            val_b = read_sstring(f)
            if strict_hash and fnv1a_32(key_b) != h:
                k = key_b.decode('utf-8', 'replace')
                raise ValueError(f'[{i}] hash mismatch for key {k!r}')
            entries.append((key_b.decode('utf-8'), val_b.decode('utf-8')))

    with open(txt_path, 'w', encoding='utf-8', newline='\n') as o:
        for k, v in entries:
            k = k.replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')
            v = v.replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')
            o.write(f'{k}:={v}\n')

def parse_txt(path: str):
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip('\n')
            if ln == 1: line = line.lstrip('\ufeff')
            if not line: continue
            
            if ':=' not in line:
                raise ValueError(f'line {ln}: no := separator')

            k, v = line.split(':=', 1)
            
            key = k.replace('\\t', '\t').replace('\\n', '\n').replace('\\r', '\r')
            val = v.replace('\\t', '\t').replace('\\n', '\n').replace('\\r', '\r')

            entries.append((key, val))
    return entries

def import_from_txt(txt_path: str, bin_path: str):
    items = parse_txt(txt_path)

    prepared = []
    for key, val in items:
        kb = key.encode('utf-8')
        vb = val.encode('utf-8')
        h = fnv1a_32(kb)
        prepared.append((h, kb, vb, key))

    with open(bin_path, 'wb') as f:
        f.write(b'\x00' * 8)
        for h, kb, vb, *_ in prepared:
            f.write(p32be(h))
            write_sstring(f, kb)
            write_sstring(f, vb)
        size = f.tell()
        count = len(prepared)
        f.seek(0)
        f.write(p32le(size))
        f.write(p32be(count))

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description='Indiana Jones and the Great Circle stings converter')
    sub = ap.add_subparsers(dest='cmd', required=True)

    e = sub.add_parser('export', help='bin → txt')
    e.add_argument('bin')
    e.add_argument('txt')

    i = sub.add_parser('import', help='txt → bin')
    i.add_argument('txt')
    i.add_argument('bin')

    args = ap.parse_args()
    if args.cmd == 'export':
        export_to_txt(args.bin, args.txt, False)
    else:
        import_from_txt(args.txt, args.bin)

if __name__ == '__main__':
    main()