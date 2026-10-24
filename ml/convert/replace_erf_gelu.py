"""Replace Erf nodes with the tanh approximation of GELU.

TFLite has no native Erf op, so the TensorFlow converter emits FlexErf, which
requires the huge Select TF Ops delegate and cannot run in tflite_flutter.
CLIP's GELU uses Erf; replacing it with the standard tanh approximation keeps
the graph numerically close while staying inside standard TFLite ops:

    erf(z) ~= tanh(sqrt(2/pi) * (sqrt(2)*z + 0.044715*(sqrt(2)*z)^3))

Usage (from ml/):
    .venv/Scripts/python.exe convert/replace_erf_gelu.py \
        --in models/tinyclip_40m32_image.onnx \
        --out models/tinyclip_40m32_image_noerf.onnx
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import onnx
from onnx import helper, numpy_helper

ROOT = Path(__file__).resolve().parents[1]


def add_const(graph: onnx.GraphProto, name: str, value: float) -> None:
    graph.initializer.append(
        numpy_helper.from_array(
            np.array(value, dtype=np.float32), name=name
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--in", dest="input", default=str(ROOT / "models" / "tinyclip_40m32_image.onnx")
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "models" / "tinyclip_40m32_image_noerf.onnx"),
    )
    args = parser.parse_args()

    model = onnx.load(args.input)
    graph = model.graph
    constants = {
        "erf_a": math.sqrt(2.0),
        "erf_b": 0.044715,
        "erf_k": math.sqrt(2.0 / math.pi),
    }
    for name, value in constants.items():
        if not any(init.name == name for init in graph.initializer):
            add_const(graph, name, value)

    replacements = 0
    new_nodes = []
    for node in graph.node:
        if node.op_type != "Erf":
            new_nodes.append(node)
            continue
        z = node.input[0]
        out = node.output[0]
        prefix = f"erf_fix_{replacements}"
        t = f"{prefix}_t"
        t2 = f"{prefix}_t2"
        t3 = f"{prefix}_t3"
        bt3 = f"{prefix}_bt3"
        s = f"{prefix}_s"
        sk = f"{prefix}_sk"
        new_nodes.extend(
            [
                helper.make_node("Mul", [z, "erf_a"], [t], name=f"{prefix}_mul_a"),
                helper.make_node("Mul", [t, t], [t2], name=f"{prefix}_mul_t2"),
                helper.make_node("Mul", [t2, t], [t3], name=f"{prefix}_mul_t3"),
                helper.make_node("Mul", [t3, "erf_b"], [bt3], name=f"{prefix}_mul_b"),
                helper.make_node("Add", [t, bt3], [s], name=f"{prefix}_add"),
                helper.make_node("Mul", [s, "erf_k"], [sk], name=f"{prefix}_mul_k"),
                helper.make_node("Tanh", [sk], [out], name=f"{prefix}_tanh"),
            ]
        )
        replacements += 1

    del graph.node[:]
    graph.node.extend(new_nodes)
    onnx.checker.check_model(model)
    onnx.save(model, args.out)
    print(f"replaced {replacements} Erf nodes -> {args.out}")

    # Numerical check against the original model.
    import onnxruntime as ort

    original = ort.InferenceSession(args.input, providers=["CPUExecutionProvider"])
    patched = ort.InferenceSession(args.out, providers=["CPUExecutionProvider"])
    x = np.random.default_rng(0).random((1, 3, 224, 224), dtype=np.float32)
    a = original.run(None, {"image": x})[0]
    b = patched.run(None, {"image": x})[0]
    cosine = float(np.sum(a * b, axis=-1)[0])
    print(f"cosine original vs tanh-GELU: {cosine:.8f}")
    if cosine < 0.99999:
        raise SystemExit("tanh approximation deviates too much")


if __name__ == "__main__":
    main()
