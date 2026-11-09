#!/usr/bin/env python3
"""Baixa as bases oficiais e gera os arquivos leves que o app Cidadania lê em data/.

Fontes:
- TSE (Tribunal Superior Eleitoral): candidatos eleitos em 2022, 2024 e 2026.
- Câmara dos Deputados: deputados em exercício, proposições e votações nominais.
- Senado Federal: senadores em exercício.

Só usa a biblioteca padrão do Python. Cada fonte é independente: se uma falhar,
as outras seguem e o erro fica registrado em data/meta.json.
"""
import csv, io, json, os, re, sys, tempfile, time, unicodedata, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RAIZ, "data")
UA = {"User-Agent": "CidadaniaApp/1.0 (+https://thephilosopherx.github.io/cidadania/)", "Accept": "application/json, text/csv, */*"}
ANO = datetime.now(timezone.utc).year
erros, fontes = [], {}
csv.field_size_limit(sys.maxsize)


def log(*a):
    print(*a, flush=True)


def chave(nome):
    s = unicodedata.normalize("NFD", str(nome)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def titulo(nome):
    pequenas = {"da", "de", "do", "das", "dos", "e"}
    partes = str(nome).strip().lower().split()
    return " ".join(p if (i and p in pequenas) else p[:1].upper() + p[1:] for i, p in enumerate(partes))


def baixar(url, destino=None, tentativas=4):
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                if destino:
                    with open(destino, "wb") as f:
                        while True:
                            bloco = r.read(1 << 20)
                            if not bloco:
                                break
                            f.write(bloco)
                    return destino
                return r.read()
        except Exception as e:
            log(f"  falha ({t + 1}/{tentativas}) {url}: {e}")
            time.sleep(5 * (t + 1))
    raise RuntimeError(f"não foi possível baixar {url}")


def salvar(rel, obj):
    caminho = os.path.join(DATA, rel)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    log(f"  salvo {rel} ({os.path.getsize(caminho) // 1024} KB)")


# ---------------------------------------------------------------- TSE
ELEITO = re.compile(r"^ELEITO")


def ler_tse(ano):
    """Gera as linhas de eleitos do arquivo consulta_cand_{ano}.zip (CSV latin-1 separado por ;)."""
    url = f"https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{ano}.zip"
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False).name
    log(f"TSE {ano}: baixando {url}")
    baixar(url, tmp)
    with zipfile.ZipFile(tmp) as z:
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        # quando existe, o arquivo "BRASIL" reúne todas as UFs e a eleição presidencial
        brasil = [n for n in nomes if re.search(r"_BRASIL\.csv$", n, re.I)]
        for nome in brasil or nomes:
            with z.open(nome) as f:
                leitor = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")
                for linha in leitor:
                    if ELEITO.match((linha.get("DS_SIT_TOT_TURNO") or "").upper()):
                        yield linha
    os.remove(tmp)


def pessoa_tse(l):
    nome = l.get("NM_CANDIDATO") or ""
    urna = l.get("NM_URNA_CANDIDATO") or nome
    return {"n": titulo(nome), "u": titulo(urna), "p": (l.get("SG_PARTIDO") or "").strip(),
            "e": (l.get("DT_ELEICAO") or "").strip(), "sq": (l.get("SQ_CANDIDATO") or "").strip()}


def data_iso(d):
    try:
        return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return d


partidos = {}


def registra_partido(l):
    sg, nm = (l.get("SG_PARTIDO") or "").strip(), (l.get("NM_PARTIDO") or "").strip()
    if sg and nm:
        partidos[sg] = titulo(nm)


def municipais(ano=2024):
    municipios = defaultdict(dict)
    for l in ler_tse(ano):
        registra_partido(l)
        uf, mun, cargo = l["SG_UF"], l["NM_UE"], (l.get("DS_CARGO") or "").upper()
        reg = municipios[uf].setdefault(chave(mun), {"nome": titulo(mun), "vereadores": {}})
        p = pessoa_tse(l)
        p["e"] = data_iso(p["e"])
        if cargo == "PREFEITO" or cargo == "VICE-PREFEITO":
            k = "prefeito" if cargo == "PREFEITO" else "vice"
            # eleição suplementar mais recente substitui a ordinária
            if k not in reg or p["e"] >= reg[k]["e"]:
                reg[k] = p
                if "SUPLEMENTAR" in (l.get("NM_TIPO_ELEICAO") or "").upper():
                    reg[k]["sup"] = 1
        elif cargo == "VEREADOR":
            reg["vereadores"][p["sq"]] = p
    total = 0
    for uf, muns in municipios.items():
        for reg in muns.values():
            reg["vereadores"] = sorted(reg["vereadores"].values(), key=lambda x: x["u"])
            for p in [reg.get("prefeito"), reg.get("vice"), *reg["vereadores"]]:
                if p:
                    p.pop("sq", None)
        total += len(muns)
        salvar(f"municipios/{uf}.json", muns)
    fontes["tse_municipal"] = {"ano": ano, "municipios": total}


def gerais(ano):
    est = defaultdict(lambda: {"governador": None, "vice": None, "senadores": [], "deputados_estaduais": [], "deputados_federais": []})
    br = {"presidente": None, "vice": None}
    for l in ler_tse(ano):
        registra_partido(l)
        cargo, uf = (l.get("DS_CARGO") or "").upper(), l.get("SG_UF")
        p = pessoa_tse(l)
        p.pop("sq", None)
        p["e"] = data_iso(p["e"])
        if cargo == "PRESIDENTE":
            br["presidente"] = p
        elif cargo == "VICE-PRESIDENTE":
            br["vice"] = p
        elif cargo == "GOVERNADOR":
            est[uf]["governador"] = p
        elif cargo == "VICE-GOVERNADOR":
            est[uf]["vice"] = p
        elif cargo == "SENADOR":
            est[uf]["senadores"].append(p)
        elif cargo in ("DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL"):
            est[uf]["deputados_estaduais"].append(p)
        elif cargo == "DEPUTADO FEDERAL":
            est[uf]["deputados_federais"].append(p)
    for e in est.values():
        for k in ("senadores", "deputados_estaduais", "deputados_federais"):
            e[k].sort(key=lambda x: x["u"])
    return dict(est), br


# ---------------------------------------------------------------- Câmara
CAMARA = "https://dadosabertos.camara.leg.br"


def camara_csv(nome, ano):
    url = f"{CAMARA}/arquivos/{nome}/csv/{nome}-{ano}.csv"
    try:
        dados = baixar(url)
    except Exception as e:
        erros.append(f"Câmara {nome}-{ano}: {e}")
        return []
    texto = dados.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(texto), delimiter=";"))


def situacao(desc):
    d = (desc or "").lower()
    if "transformad" in d and "norma" in d:
        return "Virou lei"
    if any(x in d for x in ("arquivad", "retirad", "rejeitad", "devolvid", "prejudicad")):
        return "Arquivado ou rejeitado"
    return "Em tramitação"


def camara():
    log("Câmara: deputados em exercício")
    deputados, url = [], f"{CAMARA}/api/v2/deputados?itens=100&ordem=ASC&ordenarPor=nome"
    while url:
        j = json.loads(baixar(url))
        deputados += j.get("dados", [])
        url = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
    deps = {d["id"]: {"id": d["id"], "n": d.get("nome"), "p": d.get("siglaPartido"), "uf": d.get("siglaUf"),
                      "email": d.get("email") or "", "pls": {"total": 0, "lei": 0, "arq": 0, "tram": 0, "ult": []},
                      "votos": [], "part": None} for d in deputados}
    log(f"  {len(deps)} deputados")

    anos = list(range(2023, ANO + 1))
    props = {}
    for a in anos:
        for p in camara_csv("proposicoes", a):
            if p.get("siglaTipo") in ("PL", "PLP", "PEC"):
                props[p.get("id")] = p
    vistos = set()
    for a in anos:
        for au in camara_csv("proposicoesAutores", a):
            try:
                did = int(au.get("idDeputadoAutor") or 0)
            except ValueError:
                continue
            if did not in deps or str(au.get("ordemAssinatura")).split(".")[0] != "1":
                continue
            if (did, au.get("idProposicao")) in vistos:
                continue
            vistos.add((did, au.get("idProposicao")))
            p = props.get(au.get("idProposicao"))
            if not p:
                continue
            st = situacao(p.get("ultimoStatus_descricaoSituacao"))
            reg = deps[did]["pls"]
            reg["total"] += 1
            reg[{"Virou lei": "lei", "Arquivado ou rejeitado": "arq"}.get(st, "tram")] += 1
            reg["ult"].append({"t": f'{p.get("siglaTipo")} {p.get("numero")}/{p.get("ano")}', "id": p.get("id"),
                               "ementa": (p.get("ementa") or "")[:180], "st": st, "d": (p.get("dataApresentacao") or "")[:10]})
    for d in deps.values():
        d["pls"]["ult"] = sorted(d["pls"]["ult"], key=lambda x: x["d"], reverse=True)[:6]

    plen = {}
    for a in anos[-2:]:
        for v in camara_csv("votacoes", a):
            if (v.get("siglaOrgao") or "").upper() == "PLEN":
                desc = re.sub(r"\s+", " ", (v.get("descricao") or v.get("ultimaApresentacaoProposicao_descricao") or "").replace("•", " ")).strip()
                plen[v.get("id")] = {"d": (v.get("data") or v.get("dataHoraRegistro") or "")[:10], "desc": desc[:180]}
    contados = defaultdict(set)
    votos_com_registro = set()
    for a in anos[-2:]:
        for v in camara_csv("votacoesVotos", a):
            vid = v.get("idVotacao")
            if vid not in plen:
                continue
            votos_com_registro.add(vid)
            try:
                did = int(v.get("deputado_id") or 0)
            except ValueError:
                continue
            if did in deps:
                contados[did].add(vid)
                deps[did]["votos"].append({"vid": vid, "v": v.get("voto"), **plen[vid]})
    n_plen = len(votos_com_registro)
    for did, d in deps.items():
        d["votos"] = sorted(d["votos"], key=lambda x: x["d"], reverse=True)[:8]
        for x in d["votos"]:
            x.pop("vid", None)
        if n_plen:
            d["part"] = round(100 * len(contados[did]) / n_plen)
    fontes["camara"] = {"deputados": len(deps), "proposicoes": len(props), "votacoes_plenario_com_votos": n_plen, "anos": anos}
    salvar("deputados.json", sorted(deps.values(), key=lambda x: x["n"] or ""))


# ---------------------------------------------------------------- Senado
def senado():
    log("Senado: senadores em exercício")
    j = json.loads(baixar("https://legis.senado.leg.br/dadosabertos/senador/lista/atual.json"))
    lista = j["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    sens = []
    for s in lista:
        i = s.get("IdentificacaoParlamentar", {})
        sens.append({"id": i.get("CodigoParlamentar"), "n": i.get("NomeParlamentar"), "p": i.get("SiglaPartidoParlamentar"),
                     "uf": i.get("UfParlamentar"), "email": i.get("EmailParlamentar") or "",
                     "url": i.get("UrlPaginaParlamentar") or ""})
    fontes["senado"] = {"senadores": len(sens)}
    salvar("senadores.json", sorted(sens, key=lambda x: x["n"] or ""))


# ---------------------------------------------------------------- execução
def tentar(nome, f, *a):
    try:
        return f(*a)
    except Exception as e:
        log(f"ERRO em {nome}: {e}")
        erros.append(f"{nome}: {e}")


def main():
    os.makedirs(DATA, exist_ok=True)
    tentar("TSE municipal 2024", municipais, 2024)
    estados = {}
    r = tentar("TSE 2022", gerais, 2022)
    if r:
        est, br = r
        estados = {uf: {"atual": v} for uf, v in est.items() if uf not in ("BR", "ZZ", "VT")}
        estados["BR"] = {"atual": br}
        fontes["tse_geral_2022"] = {"ufs": len(est)}
    r = tentar("TSE 2026", gerais, 2026)
    if r:
        est, br = r
        for uf, v in est.items():
            if uf in ("BR", "ZZ", "VT"):
                continue
            estados.setdefault(uf, {})["eleitos2026"] = v
        if br.get("presidente"):
            estados.setdefault("BR", {})["eleitos2026"] = br
        fontes["tse_geral_2026"] = {"ufs": len(est)}
    if estados:
        salvar("estados.json", estados)
    tentar("Câmara", camara)
    tentar("Senado", senado)
    if partidos:
        salvar("partidos.json", {k: v for k, v in partidos.items() if k})
    salvar("meta.json", {"atualizado": datetime.now(timezone.utc).isoformat(timespec="minutes"), "fontes": fontes, "erros": erros})
    log("Concluído." + (f" {len(erros)} erro(s)." if erros else ""))


if __name__ == "__main__":
    main()
