#!/usr/bin/env python3
import json
import os
from pathlib import Path


def generate_build_matrix() -> list:
    matrix_path = Path(__file__).parent.parent / "config" / "matrix.json"
    with open(matrix_path, 'r') as f:
        matrix = json.load(f)

    builds = []
    for key, configs in matrix.items():
        android, kernel = key.split('-')
        for cfg in configs:
            build = {"android": android, "kernel": kernel, "sub_level": cfg["sub_level"], "os_patch": cfg["os_patch_level"]}
            if "revision" in cfg:
                build["revision"] = cfg["revision"]
            builds.append(build)
    return builds


def save_matrix_output():
    builds = generate_build_matrix()
    output = 'matrix=' + json.dumps(builds)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(output + '\n')
    print("Matrix generated:", len(builds), "builds")


if __name__ == '__main__':
    save_matrix_output()
