"""Compacta data.json a arrays chicos para embeber en el dashboard."""
import json
from pathlib import Path

base = Path(__file__).parent
d = json.load(open(base / "data.json"))

MAQ = {1:"MK9-1",2:"MK9-2",3:"HLP-1",4:"HLP-2",5:"AMF 3000 GD2",6:"AMF 3000 Paper",
       7:"AMF 3000 GD1",8:"AMF 5000 GD1",9:"AMF 5000 GD2",10:"Filtrera Polaris",
       13:"Protos",14:"Filtrera Molins 1C",15:"Paper",16:"GD1 AMF 5000-3000",
       17:"GD2 AMF 5000-3000",18:"Filtrera Molins 2C"}
MARCAS = {6:"Melbourne Red",7:"Melbourne Gold",8:"Melbourne Mint",9:"Milenio Red",
          10:"Milenio Gold",11:"Milenio Mint",12:"Milenio Click",13:"Mill",14:"Bold Red",
          15:"Bold Mint",16:"Mill Red",17:"Mill Explosion",18:"Milenio Click PY",
          19:"Milenio Pink",20:"Milenio Vid",40:"Mill Flama",42:"Milenio Icergy Pink",
          43:"Milenio Icergy",44:"Milenio Gold Flama",45:"Milenio Click PY-1",
          47:"Melbourne Mint Flama",48:"Click Flama",49:"Milenio Icergy PY",50:"Mill Mint"}
TIPO = {1:"Cigarrilleras",2:"Cigarrilleras",13:"Cigarrilleras",
        3:"Empaquetadoras",4:"Empaquetadoras",5:"Empaquetadoras",6:"Empaquetadoras",
        7:"Empaquetadoras",8:"Empaquetadoras",9:"Empaquetadoras",15:"Empaquetadoras",
        16:"Empaquetadoras",17:"Empaquetadoras",
        10:"Filtreras",14:"Filtreras",18:"Filtreras"}
TURNOS = ["TD", "TJ", "TN"]
ti = {t: i for i, t in enumerate(TURNOS)}

def day(f):
    return f[:10]

def num(v):
    if v is None:
        return None
    f = float(v)
    return int(f) if f == int(f) else round(f, 2)

out = {
    "maquinas": {str(k): v for k, v in MAQ.items()},
    "tipoMaquina": {str(k): v for k, v in TIPO.items()},
    "marcas": {str(k): v for k, v in MARCAS.items()},
    "turnos": TURNOS,
    "plan": [[day(r["Fecha"]), r["Id_Marca"], num(r["CantidadAProducir"])] for r in d["plan"] if r["CantidadAProducir"]],
    "real": [[day(r["Fecha"]), r["Id_Marca"], num(r["CantidadProducida"])] for r in d["real"] if r["CantidadProducida"]],
    "rend": [[day(r["Fecha"]), r["id_maquina"], ti[r["Turno"]], num(r["Eficiencia"]), num(r["RendimientoDeseado"]), num(r["VelocidadDeseado"])]
             for r in d["rendimiento"] if r["Eficiencia"] not in (None, 0)],
    "prod": [[day(r["Fecha"]), r["Id_Maquina"], ti[r["Turno"]], num(r["CantidadProducida"])]
             for r in d["prod_turno"] if r["CantidadProducida"]],
    "tabaco": [[day(r["Fecha"]), num(r["ConsumoTeoricoKg"]), num(r["ConsumoRealKg"])]
               for r in d["tabaco"] if r["ConsumoTeoricoKg"] or r["ConsumoRealKg"]],
}
js = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
(base / "compact.json").write_text(js)
print("filas:", {k: len(v) for k, v in out.items() if isinstance(v, list)})
print("bytes:", len(js))
maxf = max(r[0] for r in out["real"])
print("ultima fecha real:", maxf, "| rend:", max(r[0] for r in out["rend"]), "| prod:", max(r[0] for r in out["prod"]))
