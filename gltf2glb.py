import argparse
import os
import json
import sys


def loadBinary(path):
    with open(path, 'rb') as fp:
        data = fp.read()
    return data


def loadGltf(gltf_path, data_dir):
    gltf = {'json': '', 'bin': '', 'textures': []}
    with open(gltf_path, 'r') as fp:
        gltf['json'] = json.load(fp)
    texture_names = []
    bin_name = ''
    for filename in os.listdir(data_dir):
        base, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext == '.bin':
            bin_name = filename
        elif ext in ['.png', '.jpeg', '.jpg']:
            if ext == '.png':
                mime_type = 'image/png'
            else:
                mime_type = 'image/jpeg'
            texture_names.append((filename, mime_type, filename))
    gltf['bin'] = loadBinary(os.path.join(data_dir, bin_name))
    for tex_name, mime_type, filename in texture_names:
        gltf['textures'].append(
            (filename, mime_type, loadBinary(os.path.join(data_dir, tex_name))))
    return gltf


def addHeaderAndPadding(data, header):
    chunk_size = 4 + 4 + len(data)
    before_padded_size = chunk_size
    padding_num = 0
    if chunk_size % 4 != 0:
        padding_num = 4 - (chunk_size % 4)
    padchar = 0xff  # invalid
    if header == 0x4E4F534A:
        # json case
        padchar = 0x20  # 0x20  # ' '
        # padchar = ord(' ')
    elif header == 0x004E4942:
        # bin case
        padchar = 0x00
    else:
        raise Exception()
    padchar_byte = (padchar).to_bytes(
        1, byteorder=sys.byteorder, signed=False)  # TODO: singed is True?

    chunk_size_bytes = (before_padded_size + padding_num - 8).to_bytes(
        4, byteorder=sys.byteorder, signed=False)  # With padding but without size/header size (-8)
    header_bytes = (header).to_bytes(
        4, byteorder=sys.byteorder, signed=False)
    for _ in range(padding_num):
        data = data + padchar_byte
    combined = chunk_size_bytes + header_bytes + data
    return combined, before_padded_size


def gltf2glb(gltf):
    # Add textures to bin
    bvs = gltf['json']['bufferViews']
    for texture in gltf['textures']:
        filename, mime_type, data = texture
        # Update bufferViews
        last_bv = bvs[-1]
        byteLength = len(data)
        # With assumption that
        # 1. bufferViews are sorted
        # 2. single .bin
        byteOffset = int(last_bv['byteOffset']) + int(last_bv['byteLength'])
        bv = {'buffer': 0, 'byteLength': byteLength, 'byteOffset': byteOffset}
        bvs.append(bv)
        bv_id = len(bvs) - 1

        # Update images
        images = gltf['json']['images']
        found = False
        for i, image in enumerate(images):
            if 'uri' not in image:
                continue
            if filename == image['uri']:
                new_image = {'mimeType': mime_type,
                             'name': image['name'], 'bufferView': bv_id}
                images[i] = new_image
                found = True
                break
        if not found:
            raise Exception()
        gltf['json']['images'] = images

        # Update bin
        gltf['bin'] += data
    gltf['json']['bufferViews'] = bvs

    bin_header = 0x004E4942  # 0x004E4942 -> "BIN" in ASCII
    bin_chunk, bin_before_padded_size = addHeaderAndPadding(
        gltf['bin'], bin_header)

    gltf['json']['buffers'][0]['byteLength'] = bin_before_padded_size
    if 'uri' in gltf['json']['buffers'][0]:
        del gltf['json']['buffers'][0]['uri']

    json_hader = 0x4E4F534A  # 0x4E4F534A	-> "JSON" in ASCII
    json_string = json.dumps(gltf['json'])
    with open('tmp.json', 'w') as fp:
        fp.write(json_string)
    json_data = bytes(json_string, encoding='utf-8')
    json_chunk, _ = addHeaderAndPadding(json_data, json_hader)

    magic = 0x46546C67  # 0x46546C67 -> "glTF"in ASCII
    version = 2
    header_size = 12
    length = header_size + len(json_chunk) + len(bin_chunk)
    header_data = (magic).to_bytes(4, byteorder=sys.byteorder, signed=False) +\
        (version).to_bytes(4, byteorder=sys.byteorder, signed=False) +\
        (length).to_bytes(4, byteorder=sys.byteorder, signed=False)
    glb = header_data + json_chunk + bin_chunk

    return glb


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert gltf to glb')
    parser.add_argument(
        'src', type=str, help='path to source .gltf. All referred files must be placed in the same directory')
    parser.add_argument('dst', type=str, help='path to output .glb')
    parser.add_argument("--src_dir",
                        help="directory containing .bin and textures")
    args = parser.parse_args()
    if args.src_dir:
        src_dir = args.src_dir
    else:
        src_dir = os.path.dirname(args.src)
    gltf = loadGltf(args.src, src_dir)
    glb = gltf2glb(gltf)
    with open(args.dst, 'wb') as fp:
        fp.write(glb)
