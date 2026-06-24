from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


PLY_TO_DTYPE = {
    "char": "i1",
    "int8": "i1",
    "uchar": "u1",
    "uint8": "u1",
    "short": "<i2",
    "int16": "<i2",
    "ushort": "<u2",
    "uint16": "<u2",
    "int": "<i4",
    "int32": "<i4",
    "uint": "<u4",
    "uint32": "<u4",
    "float": "<f4",
    "float32": "<f4",
    "double": "<f8",
    "float64": "<f8",
}

DTYPE_TO_PLY = {
    "i1": "char",
    "u1": "uchar",
    "i2": "short",
    "u2": "ushort",
    "i4": "int",
    "u4": "uint",
    "f4": "float",
    "f8": "double",
}


@dataclass(frozen=True)
class PlyProperty:
    ply_type: str
    name: str


@dataclass
class SplatPly:
    path: Path | None
    format_name: str
    version: str
    comments: list[str]
    properties: list[PlyProperty]
    data: np.ndarray

    @property
    def property_names(self) -> list[str]:
        return [prop.name for prop in self.properties]

    @property
    def vertex_count(self) -> int:
        return int(self.data.shape[0])


def _dtype_for_properties(properties: Iterable[PlyProperty]) -> np.dtype:
    fields = []
    for prop in properties:
        try:
            dtype_code = PLY_TO_DTYPE[prop.ply_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported PLY scalar type: {prop.ply_type}") from exc
        fields.append((prop.name, dtype_code))
    return np.dtype(fields)


def _parse_header(handle) -> tuple[str, str, list[str], int, list[PlyProperty]]:
    first = handle.readline().decode("ascii").strip()
    if first != "ply":
        raise ValueError("Not a PLY file")

    format_name = ""
    version = ""
    comments: list[str] = []
    vertex_count: int | None = None
    properties: list[PlyProperty] = []
    current_element: str | None = None

    while True:
        raw = handle.readline()
        if not raw:
            raise ValueError("Unexpected end of file while reading PLY header")

        line = raw.decode("ascii").strip()
        if line == "end_header":
            break

        parts = line.split()
        if not parts:
            continue

        tag = parts[0]
        if tag == "format":
            if len(parts) != 3:
                raise ValueError(f"Malformed PLY format line: {line}")
            format_name, version = parts[1], parts[2]
        elif tag == "comment":
            comments.append(line[len("comment") :].strip())
        elif tag == "element":
            if len(parts) != 3:
                raise ValueError(f"Malformed PLY element line: {line}")
            current_element = parts[1]
            if current_element == "vertex":
                vertex_count = int(parts[2])
            else:
                raise ValueError(
                    "Only vertex-only 3DGS PLY files are supported; "
                    f"found extra element {current_element!r}"
                )
        elif tag == "property":
            if current_element != "vertex":
                continue
            if len(parts) != 3:
                raise ValueError(f"Only scalar vertex properties are supported: {line}")
            properties.append(PlyProperty(parts[1], parts[2]))

    if not format_name or not version:
        raise ValueError("PLY header did not include a format line")
    if vertex_count is None:
        raise ValueError("PLY header did not include an element vertex line")
    if not properties:
        raise ValueError("PLY file has no vertex properties")
    return format_name, version, comments, vertex_count, properties


def read_ply(path: str | Path) -> SplatPly:
    path = Path(path)
    with path.open("rb") as handle:
        format_name, version, comments, vertex_count, properties = _parse_header(handle)
        dtype = _dtype_for_properties(properties)

        if format_name == "binary_little_endian":
            data = np.fromfile(handle, dtype=dtype, count=vertex_count)
        elif format_name == "ascii":
            rows = []
            for _ in range(vertex_count):
                line = handle.readline().decode("ascii")
                if not line:
                    raise ValueError("Unexpected EOF while reading ASCII PLY data")
                rows.append(tuple(float(x) for x in line.split()))
            data = np.array(rows, dtype=dtype)
        else:
            raise ValueError(f"Unsupported PLY format: {format_name}")

    if data.shape[0] != vertex_count:
        raise ValueError(f"Expected {vertex_count} vertices, read {data.shape[0]}")

    return SplatPly(path, format_name, version, comments, properties, data)


def write_ply(cloud: SplatPly, path: str | Path, comments: Iterable[str] = ()) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    properties = cloud.properties
    vertex_count = cloud.vertex_count

    all_comments = list(cloud.comments)
    all_comments.extend(comments)

    header_lines = [
        "ply",
        f"format {cloud.format_name} {cloud.version}",
    ]
    header_lines.extend(f"comment {comment}" for comment in all_comments if comment)
    header_lines.append(f"element vertex {vertex_count}")
    header_lines.extend(f"property {prop.ply_type} {prop.name}" for prop in properties)
    header_lines.append("end_header")
    header = ("\n".join(header_lines) + "\n").encode("ascii")

    with path.open("wb") as handle:
        handle.write(header)
        if cloud.format_name == "binary_little_endian":
            dtype = _dtype_for_properties(properties)
            cloud.data.astype(dtype, copy=False).tofile(handle)
        elif cloud.format_name == "ascii":
            for row in cloud.data:
                values = [str(row[prop.name].item()) for prop in properties]
                handle.write((" ".join(values) + "\n").encode("ascii"))
        else:
            raise ValueError(f"Unsupported PLY format: {cloud.format_name}")


def make_cloud(data: np.ndarray, properties: list[PlyProperty]) -> SplatPly:
    return SplatPly(
        path=None,
        format_name="binary_little_endian",
        version="1.0",
        comments=[],
        properties=properties,
        data=data,
    )


def infer_properties_from_dtype(dtype: np.dtype) -> list[PlyProperty]:
    properties = []
    for name in dtype.names or ():
        field_dtype = np.dtype(dtype.fields[name][0])
        key = field_dtype.str[-2:]
        if field_dtype.kind in {"i", "u", "f"}:
            ply_type = DTYPE_TO_PLY.get(key)
            if ply_type is None:
                raise ValueError(f"Cannot map dtype {field_dtype} to PLY type")
            properties.append(PlyProperty(ply_type, name))
        else:
            raise ValueError(f"Unsupported dtype for PLY field {name}: {field_dtype}")
    return properties

