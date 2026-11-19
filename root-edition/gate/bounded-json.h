#ifndef CYTV_GATE_BOUNDED_JSON_H
#define CYTV_GATE_BOUNDED_JSON_H

#include <string.h>

#define CYTV_JSON_LIMIT 16384

/* Bounded JSON parser. Keys are unescaped ASCII; duplicate keys are rejected.
 */
struct jt {
  int start, end, next, children;
  char type;
};
struct json {
  const char *s;
  int p, n, count;
  struct jt t[512];
};
static void ws(struct json *j) {
  while (j->p < j->n && strchr(" \t\r\n", j->s[j->p]))
    j->p++;
}
static int value(struct json *j, int depth);
static int string(struct json *j, int key) {
  int start = j->p++;
  while (j->p < j->n) {
    unsigned char c = (unsigned char)j->s[j->p++];
    if (c == '"')
      return start;
    if (c < 32 || c >= 128)
      return -1;
    if (c == '\\') {
      if (key || j->p >= j->n)
        return -1;
      char e = j->s[j->p++];
      if (strchr("\"\\/bfnrt", e))
        continue;
      if (e != 'u' || j->p + 4 > j->n)
        return -1;
      for (int x = 0; x < 4; x++)
        if (!strchr("0123456789abcdefABCDEF", j->s[j->p++]))
          return -1;
    }
  }
  return -1;
}
static int value(struct json *j, int depth) {
  ws(j);
  if (depth > 16 || j->count >= 512 || j->p >= j->n)
    return -1;
  int id = j->count++;
  struct jt *t = &j->t[id];
  t->start = j->p;
  t->children = 0;
  char c = j->s[j->p];
  t->type = c;
  if (c == '{' || c == '[') {
    j->p++;
    ws(j);
    char end = c == '{' ? '}' : ']';
    if (j->p < j->n && j->s[j->p] == end)
      j->p++;
    else
      for (;;) {
        if (c == '{') {
          ws(j);
          if (j->p >= j->n || j->s[j->p] != '"' || j->count >= 512)
            return -1;
          int k = j->count++;
          j->t[k].start = j->p;
          if (string(j, 1) < 0)
            return -1;
          j->t[k].end = j->p;
          j->t[k].next = k + 1;
          j->t[k].type = '"';
          for (int old = id + 1; old < k; old = j->t[old + 1].next) {
            int a = j->t[old].start, b = j->t[old].end;
            if (b - a == j->p - j->t[k].start &&
                !memcmp(j->s + a, j->s + j->t[k].start, (size_t)(b - a)))
              return -1;
          }
          ws(j);
          if (j->p >= j->n || j->s[j->p++] != ':')
            return -1;
        }
        if (value(j, depth + 1) < 0)
          return -1;
        t->children++;
        ws(j);
        if (j->p >= j->n)
          return -1;
        if (j->s[j->p] == end) {
          j->p++;
          break;
        }
        if (j->s[j->p++] != ',')
          return -1;
      }
  } else if (c == '"') {
    if (string(j, 0) < 0)
      return -1;
  } else if (c == 't' || c == 'f' || c == 'n') {
    const char *s = c == 't' ? "true" : c == 'f' ? "false" : "null";
    int n = (int)strlen(s);
    if (j->n - j->p < n || memcmp(j->s + j->p, s, (size_t)n))
      return -1;
    j->p += n;
  } else {
    int p = j->p;
    if (j->s[j->p] == '-')
      j->p++;
    if (j->p >= j->n)
      return -1;
    if (j->s[j->p] == '0')
      j->p++;
    else {
      if (j->s[j->p] < '1' || j->s[j->p] > '9')
        return -1;
      while (j->p < j->n && j->s[j->p] >= '0' && j->s[j->p] <= '9')
        j->p++;
    }
    if (j->p < j->n && j->s[j->p] == '.') {
      j->p++;
      int b = j->p;
      while (j->p < j->n && j->s[j->p] >= '0' && j->s[j->p] <= '9')
        j->p++;
      if (b == j->p)
        return -1;
    }
    if (j->p < j->n && (j->s[j->p] == 'e' || j->s[j->p] == 'E')) {
      j->p++;
      if (j->p < j->n && (j->s[j->p] == '+' || j->s[j->p] == '-'))
        j->p++;
      int b = j->p;
      while (j->p < j->n && j->s[j->p] >= '0' && j->s[j->p] <= '9')
        j->p++;
      if (b == j->p)
        return -1;
    }
    if (j->p == p)
      return -1;
    t->type = '0';
  }
  t->end = j->p;
  t->next = j->count;
  return id;
}
static int parse(struct json *j, const char *s) {
  memset(j, 0, sizeof(*j));
  size_t n = strnlen(s, CYTV_JSON_LIMIT + 1);
  if (n > CYTV_JSON_LIMIT)
    return 0;
  j->s = s;
  j->n = (int)n;
  if (value(j, 0) != 0 || j->t[0].type != '{')
    return 0;
  ws(j);
  return j->p == j->n;
}
static int field(struct json *j, int obj, const char *name) {
  if (j->t[obj].type != '{')
    return -1;
  for (int i = obj + 1; i < j->t[obj].next; i = j->t[i + 1].next) {
    struct jt *t = &j->t[i];
    if (t->end - t->start == (int)strlen(name) + 2 &&
        !memcmp(j->s + t->start + 1, name, strlen(name)))
      return i + 1;
  }
  return -1;
}
static int literal(struct json *j, int id, const char *s) {
  return id >= 0 && j->t[id].end - j->t[id].start == (int)strlen(s) &&
         !memcmp(j->s + j->t[id].start, s, strlen(s));
}

#endif
