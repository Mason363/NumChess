/* Minimal replacements for the few libc routines the app needs: much
 * smaller than newlib's speed-optimized versions. */
#include <stddef.h>

#define EXPORT __attribute__((used, externally_visible))

EXPORT void *memcpy(void *d, const void *s, size_t n) {
  char *o = d;
  const char *i = s;
  while (n--) *o++ = *i++;
  return d;
}

EXPORT void *memmove(void *d, const void *s, size_t n) {
  char *o = d;
  const char *i = s;
  if (o < i) return memcpy(d, s, n);
  while (n--) o[n] = i[n];
  return d;
}

EXPORT void *memset(void *d, int c, size_t n) {
  char *o = d;
  while (n--) *o++ = c;
  return d;
}

EXPORT size_t strlen(const char *s) {
  const char *e = s;
  while (*e) e++;
  return e - s;
}

EXPORT char *strcpy(char *d, const char *s) {
  char *o = d;
  while ((*o++ = *s++)) {}
  return d;
}
