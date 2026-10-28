"""Rampa de gamma compartilhada (wlr-gamma-control) com nivel do preto.

Replica a matematica de cor do wl-gammarelay-rs e permite adicionar um
pedestal de preto (black) por canal, comprimindo o topo por (1-black) para
nao estourar o branco.

Uso:
    from ramp import fill_ramp
    data = fill_ramp(size, temp, gamma, brightness, inverted, black)

`data` sao 3*size uint16 (R, depois G, depois B), pronto para o set_gamma.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys

__all__ = ["BLACKBODY", "fill_ramp"]

# [Black body radiation color](https://en.wikipedia.org/wiki/Black-body_radiation)
# para 1000K..10100K em passos de 100K (mesma tabela do wl-gammarelay-rs).
BLACKBODY = (
    1.00000000, 0.18172716, 0.00000000, 1.00000000, 0.25503671, 0.00000000,
    1.00000000, 0.30942099, 0.00000000, 1.00000000, 0.35357379, 0.00000000,
    1.00000000, 0.39091524, 0.00000000, 1.00000000, 0.42322816, 0.00000000,
    1.00000000, 0.45159884, 0.00000000, 1.00000000, 0.47675916, 0.00000000,
    1.00000000, 0.49923747, 0.00000000, 1.00000000, 0.51943421, 0.00000000,
    1.00000000, 0.54360078, 0.08679949, 1.00000000, 0.56618736, 0.14065513,
    1.00000000, 0.58734976, 0.18362641, 1.00000000, 0.60724493, 0.22137978,
    1.00000000, 0.62600248, 0.25591950, 1.00000000, 0.64373109, 0.28819679,
    1.00000000, 0.66052319, 0.31873863, 1.00000000, 0.67645822, 0.34786758,
    1.00000000, 0.69160518, 0.37579588, 1.00000000, 0.70602449, 0.40267128,
    1.00000000, 0.71976951, 0.42860152, 1.00000000, 0.73288760, 0.45366838,
    1.00000000, 0.74542112, 0.47793608, 1.00000000, 0.75740814, 0.50145662,
    1.00000000, 0.76888303, 0.52427322, 1.00000000, 0.77987699, 0.54642268,
    1.00000000, 0.79041843, 0.56793692, 1.00000000, 0.80053332, 0.58884417,
    1.00000000, 0.81024551, 0.60916971, 1.00000000, 0.81957693, 0.62893653,
    1.00000000, 0.82854786, 0.64816570, 1.00000000, 0.83717703, 0.66687674,
    1.00000000, 0.84548188, 0.68508786, 1.00000000, 0.85347859, 0.70281616,
    1.00000000, 0.86118227, 0.72007777, 1.00000000, 0.86860704, 0.73688797,
    1.00000000, 0.87576611, 0.75326132, 1.00000000, 0.88267187, 0.76921169,
    1.00000000, 0.88933596, 0.78475236, 1.00000000, 0.89576933, 0.79989606,
    1.00000000, 0.90198230, 0.81465502, 1.00000000, 0.90963069, 0.82838210,
    1.00000000, 0.91710889, 0.84190889, 1.00000000, 0.92441842, 0.85523742,
    1.00000000, 0.93156127, 0.86836903, 1.00000000, 0.93853986, 0.88130458,
    1.00000000, 0.94535695, 0.89404470, 1.00000000, 0.95201559, 0.90658983,
    1.00000000, 0.95851906, 0.91894041, 1.00000000, 0.96487079, 0.93109690,
    1.00000000, 0.97107439, 0.94305985, 1.00000000, 0.97713351, 0.95482993,
    1.00000000, 0.98305189, 0.96640795, 1.00000000, 0.98883326, 0.97779486,
    1.00000000, 0.99448139, 0.98899179, 1.00000000, 1.00000000, 1.00000000,
    0.98947904, 0.99348723, 1.00000000, 0.97940448, 0.98722715, 1.00000000,
    0.96975025, 0.98120637, 1.00000000, 0.96049223, 0.97541240, 1.00000000,
    0.95160805, 0.96983355, 1.00000000, 0.94303638, 0.96443333, 1.00000000,
    0.93480451, 0.95923080, 1.00000000, 0.92689056, 0.95421394, 1.00000000,
    0.91927697, 0.94937330, 1.00000000, 0.91194747, 0.94470005, 1.00000000,
    0.90488690, 0.94018594, 1.00000000, 0.89808115, 0.93582323, 1.00000000,
    0.89151710, 0.93160469, 1.00000000, 0.88518247, 0.92752354, 1.00000000,
    0.87906581, 0.92357340, 1.00000000, 0.87315640, 0.91974827, 1.00000000,
    0.86744421, 0.91604254, 1.00000000, 0.86191983, 0.91245088, 1.00000000,
    0.85657444, 0.90896831, 1.00000000, 0.85139976, 0.90559011, 1.00000000,
    0.84638799, 0.90231183, 1.00000000, 0.84153180, 0.89912926, 1.00000000,
    0.83682430, 0.89603843, 1.00000000, 0.83225897, 0.89303558, 1.00000000,
    0.82782969, 0.89011714, 1.00000000, 0.82353066, 0.88727974, 1.00000000,
    0.81935641, 0.88452017, 1.00000000, 0.81530175, 0.88183541, 1.00000000,
    0.81136180, 0.87922257, 1.00000000, 0.80753191, 0.87667891, 1.00000000,
    0.80380769, 0.87420182, 1.00000000, 0.80018497, 0.87178882, 1.00000000,
    0.79665980, 0.86943756, 1.00000000, 0.79322843, 0.86714579, 1.00000000,
    0.78988728, 0.86491137, 1.00000000, 0.78663296, 0.86273225, 1.00000000,
)

C_SOURCE = r"""
#include <stdint.h>
#include <math.h>

void ws_fill_ramp(uint16_t *r, uint16_t *g, uint16_t *b, int n,
                  const double *bb, int temp, double gamma,
                  double brightness, int inverted, double black) {
    int ci = ((temp - 1000) / 100) * 3;
    double a = (temp % 100) / 100.0;
    double wr = (1.0 - a) * bb[ci]     + a * bb[ci + 3];
    double wg = (1.0 - a) * bb[ci + 1] + a * bb[ci + 4];
    double wb = (1.0 - a) * bb[ci + 2] + a * bb[ci + 5];
    double vmax = 65535.0 * brightness;
    double vmaxg = pow(vmax, 1.0 - gamma);
    double step = vmax / (double)(n - 1);
    double bl = black * 65535.0;
    double scale = 1.0 - black;
    int i;
    for (i = 0; i < n; i++) {
        double v = step * (double)i;
        int idx = inverted ? (n - 1 - i) : i;
        double vr = pow(v * wr, gamma) * vmaxg * scale + bl;
        double vg = pow(v * wg, gamma) * vmaxg * scale + bl;
        double vb = pow(v * wb, gamma) * vmaxg * scale + bl;
        if (vr < 0.0) vr = 0.0; else if (vr > 65535.0) vr = 65535.0;
        if (vg < 0.0) vg = 0.0; else if (vg > 65535.0) vg = 65535.0;
        if (vb < 0.0) vb = 0.0; else if (vb > 65535.0) vb = 65535.0;
        r[idx] = (uint16_t)vr;
        g[idx] = (uint16_t)vg;
        b[idx] = (uint16_t)vb;
    }
}
"""

_HERE = os.path.dirname(os.path.abspath(__file__))
_SO = os.path.join(_HERE, "_wsramp.so")
_C = os.path.join(_HERE, "_wsramp.c")


def _build():
    with open(_C, "w") as f:
        f.write(C_SOURCE)
    tmp = _SO + ".tmp"
    subprocess.run(
        ["cc", "-O2", "-shared", "-fPIC", "-o", tmp, _C, "-lm"],
        check=True,
    )
    os.replace(tmp, _SO)


try:
    _lib = ctypes.CDLL(_SO)
except OSError:
    _build()
    _lib = ctypes.CDLL(_SO)

_lib.ws_fill_ramp.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
    ctypes.c_void_p, ctypes.c_int, ctypes.c_double, ctypes.c_double,
    ctypes.c_int, ctypes.c_double,
]
_lib.ws_fill_ramp.restype = None

_BB = (ctypes.c_double * len(BLACKBODY))(*BLACKBODY)


def fill_ramp(size, temp, gamma, brightness, inverted=False, black=0.0):
    """Devolve 3*size uint16 (R, G, B) para a rampa de gamma."""
    if size <= 0:
        return b""
    r = (ctypes.c_uint16 * size)()
    g = (ctypes.c_uint16 * size)()
    b = (ctypes.c_uint16 * size)()
    _lib.ws_fill_ramp(r, g, b, size, _BB, int(temp), float(gamma),
                      float(brightness), 1 if inverted else 0, float(black))
    return bytes(r) + bytes(g) + bytes(b)
