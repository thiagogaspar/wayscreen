
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
