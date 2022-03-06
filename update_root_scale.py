from cmath import inf
import json
import argparse


def updateScale(gltf, dst_size):
    # Get taget node
    node = gltf["nodes"][0]

    # Get min/max and merge for each geometry
    merged_max = [-inf, -inf, -inf]
    merged_min = [inf, inf, inf]
    for acc in gltf["accessors"]:
        # Accessors specified by
        # meshes[i].primitives.attributes.POSITION
        # must have max/min
        if "max" in acc:
            cur_max = acc["max"]
            for i in range(3):
                if merged_max[i] < cur_max[i]:
                    merged_max[i] = cur_max[i]
        if "min" in acc:
            cur_min = acc["min"]
            for i in range(3):
                if cur_min[i] < merged_min[i]:
                    merged_min[i] = cur_min[i]
    org_size = []
    for i in range(3):
        org_size.append(merged_max[i] - merged_min[i])

    # Compute scale
    scale = []
    for i in range(3):
        scale.append(dst_size[i] / org_size[i])
    node["scale"] = scale

    gltf["nodes"][0] = node
    return gltf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update scale of gltf')
    parser.add_argument('src', type=str, help='path to source .gltf')
    parser.add_argument('x', type=float, help='target x')
    parser.add_argument('y', type=float, help='target y')
    parser.add_argument('z', type=float, help='target z')
    parser.add_argument('dst', type=str, help='path to output .gltf')
    args = parser.parse_args()
    src_gltf = json.load(open(args.src, 'r'))
    dst_gltf = updateScale(src_gltf, [args.x, args.y, args.z])
    with open(args.dst, 'w') as fp:
        json.dump(dst_gltf, fp, indent=2)
