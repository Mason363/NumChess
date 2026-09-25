/* Host-side engine tests: perft node counts on standard positions,
 * incremental hash/eval consistency, and a quick search benchmark. */
#include "../src/chess.c"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

uint64_t eadk_timing_millis() {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec * 1000ull + ts.tv_nsec / 1000000;
}
uint32_t eadk_random() { return (uint32_t)rand(); }
void ui_tick(void) {}

static void set_fen(const char *f) {
  memset(&P, 0, sizeof P);
  hp = 0;
  for (int r = 7, c = 0; *f && *f != ' '; f++) {
    if (*f == '/') r--, c = 0;
    else if (*f >= '1' && *f <= '8') c += *f - '0';
    else {
      const char *pcs = " PNBRQK  pnbrqk", *q = strchr(pcs, *f);
      put(r * 16 + c++, q - pcs);
    }
  }
  f++;
  P.side = *f == 'b';
  f += 2;
  for (; *f && *f != ' '; f++) P.castle |= *f == 'K' ? 1 : *f == 'Q' ? 2 : *f == 'k' ? 4 : *f == 'q' ? 8 : 0;
  f++;
  P.ep = *f == '-' ? NOSQ : (f[1] - '1') * 16 + f[0] - 'a';
  P.hash ^= Zc[P.castle];
  if (P.ep != NOSQ) P.hash ^= Zep[P.ep & 7];
  if (P.side) P.hash ^= Zside;
}

static int consistent(void) {
  Pos s = P;
  uint8_t b[128];
  memcpy(b, P.b, 128);
  memset(&P, 0, sizeof P);
  for (int i = 0; i < 128; i++)
    if (!OFF(i) && b[i]) put(i, b[i]);
  P.side = s.side, P.castle = s.castle, P.ep = s.ep, P.fifty = s.fifty;
  P.hash ^= Zc[P.castle];
  if (P.ep != NOSQ) P.hash ^= Zep[P.ep & 7];
  if (P.side) P.hash ^= Zside;
  int ok = P.hash == s.hash && P.mg == s.mg && P.eg == s.eg && P.phase == s.phase &&
           !memcmp(P.cnt, s.cnt, 16) && P.king[0] == s.king[0] && P.king[1] == s.king[1];
  P = s;
  return ok;
}

static uint64_t perft(int d) {
  Move ml[256];
  int n = legal(ml);
  if (d == 1) return n;
  uint64_t c = 0;
  for (int i = 0; i < n; i++) {
    make(ml[i]);
    if (d == 2 && !consistent()) {
      printf("inconsistent incremental state\n");
      exit(1);
    }
    c += perft(d - 1);
    unmake();
  }
  return c;
}

int main(void) {
  static const struct { const char *fen; int d; uint64_t n; } T[] = {
    {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -", 5, 4865609},
    {"r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -", 4, 4085603},
    {"8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -", 5, 674624},
    {"r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq -", 4, 422333},
    {"rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ -", 4, 2103487},
    {"r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - -", 4, 3894594},
  };
  ch_init();
  int fail = 0;
  for (unsigned i = 0; i < sizeof T / sizeof *T; i++) {
    set_fen(T[i].fen);
    uint64_t n = perft(T[i].d);
    printf("perft %u: %llu %s\n", i, (unsigned long long)n, n == T[i].n ? "ok" : "FAIL");
    fail |= n != T[i].n;
  }
  static const char *bench[] = {
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -",
    "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - -",
  };
  for (unsigned i = 0; i < 3; i++) {
    set_fen(bench[i]);
    uint64_t t = eadk_timing_millis();
    int s;
    Move m = think(7, 100000, &s);
    t = eadk_timing_millis() - t;
    char buf[16];
    san(m, buf);
    printf("bench %u: %s score %d depth %d nodes %u in %llums\n", i, buf, s, think_depth, nodes,
           (unsigned long long)t);
  }
  return fail;
}
