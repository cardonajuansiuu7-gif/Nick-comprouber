#!/usr/bin/env python3
"""
Comprobador automático de nicks de Minecraft con sentido (no fuerza bruta).

En vez de probar TODAS las combinaciones posibles de letras/números (que
son decenas de millones e imposibles de comprobar en un tiempo razonable),
este script parte de una lista de palabras reales en inglés (cortas, tipo
gamertag) y genera variantes con sentido:

  - la palabra original                (easy)
  - sustituciones estilo leetspeak     (e4sy, ea5y, 3a5y...)
  - la palabra/variante con la última letra duplicada, si así llega a
    longitud 4 o 5                     (e4syy, easyy...)

Solo se conservan variantes de 4 o 5 caracteres (se ignoran las de 3).
El resultado es un conjunto de unos pocos miles de candidatos "con
sentido", en vez de 62 millones de combinaciones aleatorias - así que
el script puede comprobarlos TODOS automáticamente en un rato razonable.

IMPORTANTE:
- La API pública de Mojang está limitada a ~600 peticiones/10 min
  (~1 por segundo). Este script respeta ese ritmo automáticamente.
- El progreso se guarda en disco (revisados.txt / disponibles.txt), así
  que puedes parar con Ctrl+C y reanudar más tarde sin repetir trabajo.

USO:
    pip install requests
    python comprobador_nicks_minecraft.py
"""

import itertools
import time
import os

import requests

API_URL = "https://api.minecraftservices.com/minecraft/profile/name/{}/available"
RATE_LIMIT_SECONDS = 1.1  # margen de seguridad sobre ~1 petición/segundo
OUTPUT_FILE = "disponibles.txt"
CHECKED_FILE = "revisados.txt"

LEET_MAP = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "g": "9", "b": "8"}

# Lista curada de palabras cortas en inglés, estilo gamertag (3-5 letras).
# Se pueden añadir/quitar palabras libremente.
PALABRAS = """
easy fast slow cool dark pale wild calm kind mean loud soft hard weak epic
huge tiny vast rare pure true fake glad sly shy bold grim keen lean neat
plain proud quick rough sharp sleek smart sour sweet tough wise brave fierce
wolf bear lion tiger hawk eagle shark snake fox owl crow raven deer moose
otter panda koala zebra whale seal frog toad bird fish bull goat lamb mule
mole bat cat dog pig cow hen ant bee fly bug moth crab clam newt lynx puma
moon star sun sky sea lake wind fire rain snow ice rock sand wave leaf tree
rose lily herb dune cave cliff peak ridge storm cloud mist dawn dusk glow
spark blaze flame frost flood quake ash fog dew rust mud gem ore coal iron
ninja ghost demon angel king queen lord hero thief mage monk sage druid elf
orc troll giant dwarf witch spirit blade sword spear arrow shield armor
cloak boots staff wand magic spell curse quest realm throne crown crypt
tomb ruin void chaos order honor glory valor wrath fury doom fate luck myth
red blue gold gray jade teal navy plum rust onyx ruby opal coral
rush dash jump leap race ride roam hunt seek find gain earn save win lose
play game ball disc code byte cyber pixel laser robot drone rocket comet
orbit nova alien atlas titan zeus thor odin loki hydra kraken phoenix viper
falcon rider slayer hunter reaper savage rebel outlaw rogue sniper striker
ranger warden guard scout medic pilot racer boxer coach champ rival legend
""".split()

PALABRAS = sorted(set(PALABRAS))


def cargar_revisados():
    if os.path.exists(CHECKED_FILE):
        with open(CHECKED_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()


def generar_variantes(palabra):
    palabra = palabra.lower()
    base_variants = {palabra}

    posiciones = [i for i, c in enumerate(palabra) if c in LEET_MAP]
    for r in range(1, len(posiciones) + 1):
        for subset in itertools.combinations(posiciones, r):
            nueva = list(palabra)
            for i in subset:
                nueva[i] = LEET_MAP[nueva[i]]
            base_variants.add("".join(nueva))

    resultado = set()
    for v in base_variants:
        resultado.add(v)
        if len(v) == 3:
            resultado.add(v + v[-1])       # -> 4
            resultado.add(v + v[-1] * 2)   # -> 5
        elif len(v) == 4:
            resultado.add(v + v[-1])       # -> 5

    return {v for v in resultado if 4 <= len(v) <= 5}


def generar_candidatos():
    candidatos = set()
    for palabra in PALABRAS:
        candidatos |= generar_variantes(palabra)
    return sorted(candidatos)


def comprobar_nombre(nombre):
    try:
        r = requests.get(API_URL.format(nombre), timeout=10)
        if r.status_code == 200:
            return "disponible"
        elif r.status_code in (400, 403):
            return "no_disponible"
        elif r.status_code == 429:
            return "rate_limited"
        else:
            return f"desconocido_{r.status_code}"
    except requests.RequestException:
        return "error_red"


def main():
    candidatos = generar_candidatos()
    print(f"Palabras base: {len(PALABRAS)}")
    print(f"Candidatos con sentido generados (4-5 chars): {len(candidatos):,}")
    print(f"Tiempo estimado: ~{len(candidatos) * RATE_LIMIT_SECONDS / 60:.1f} minutos")
    print("Comprobación automática iniciada. Ctrl+C para parar (progreso guardado).\n")

    revisados = cargar_revisados()
    checked_f = open(CHECKED_FILE, "a")
    disponibles_f = open(OUTPUT_FILE, "a")

    contador = 0
    try:
        for nombre in candidatos:
            if nombre in revisados:
                continue

            estado = comprobar_nombre(nombre)
            if estado == "rate_limited":
                print("Límite de peticiones alcanzado, esperando 60s...")
                time.sleep(60)
                estado = comprobar_nombre(nombre)

            if estado == "disponible":
                print(f"✅ DISPONIBLE: {nombre}")
                disponibles_f.write(nombre + "\n")
                disponibles_f.flush()

            checked_f.write(nombre + "\n")
            checked_f.flush()
            contador += 1
            if contador % 50 == 0:
                print(f"Comprobados: {contador:,} / {len(candidatos):,}")

            time.sleep(RATE_LIMIT_SECONDS)

        print(f"\nTerminado. Total comprobados: {contador:,}")
        print(f"Nicks disponibles guardados en: {OUTPUT_FILE}")
    except KeyboardInterrupt:
        print(f"\nDetenido por el usuario. Comprobados en esta sesión: {contador:,}")
        print(f"Nicks disponibles hasta ahora en: {OUTPUT_FILE}")
    finally:
        checked_f.close()
        disponibles_f.close()


if __name__ == "__main__":
    main()
