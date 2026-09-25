#ifndef CHESS_H
#define CHESS_H

#include <stdint.h>

enum { EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING };
#define BLACK 8
#define COLOR(p) ((p) >> 3)
#define TYPE(p) ((p) & 7)
#define NOSQ 0x80

/* 0x88 squares: sq = rank * 16 + file */
typedef uint16_t Move; /* from | to << 7 | promo << 14 (promo: 0 N, 1 B, 2 R, 3 Q) */
#define MFROM(m) ((m) & 127)
#define MTO(m) (((m) >> 7) & 127)
#define MPROMO(m) ((m) >> 14)
#define MOVE(f, t, p) ((Move)((f) | (t) << 7 | (p) << 14))

#define MATE 30000
#define INF 32000
#define MAXPLY 64
#define MAXGAME 600

typedef struct {
  uint8_t b[128];
  uint8_t side, castle, ep, fifty;
  uint8_t king[2];
  uint8_t cnt[16];
  int16_t mg, eg, phase;
  uint64_t hash;
} Pos;

typedef struct {
  uint64_t hash;
  Move m;
  uint8_t pc, cap, castle, ep, fifty;
} Undo;

extern Pos P;
extern Undo H[];
extern int hp;

enum { ONGOING, CHECKMATE, STALEMATE, FIFTY, REPETITION, MATERIAL };

void ch_init(void);
void ch_reset(void);
void make(Move m);
void unmake(void);
int in_check(void);
int legal(Move *out);
int is_legal(Move m);
int gives_check(Move m);
int status(void);
void san(Move m, char *out);

int eval(void);
int search(int depth, int alpha, int beta, int ply);
Move think(int depth, int ms, int *score);
int score_move(Move m, int depth, int alpha, int beta);
Move bot_move(int depth, int noise, int blunder, int ms);
int mate_in(int n, int checks_only);
int mate_len(int max, int checks_only);
int mated_within(int n);
Move mate_move(int n);
Move defend(int n);

typedef struct {
  Pos start;    /* position before the opponent's last move */
  Move pre;     /* that move, played when the puzzle starts */
  Move sol[5];  /* solver moves and replies */
  uint8_t nsol, mate;
  int16_t rating;
} Puzzle;
extern Puzzle PZ;
void puzzle_gen(int kind, int target);
extern int think_depth;

extern uint32_t nodes;

#endif
