/* In-process sanitizer harness for the actual production parser. */
#define main gate_command_main
#include "../gate/gate.c"
#undef main
#include <assert.h>
int main(void) {
  struct json j;
  const char *good[] = {"{}", "{\"preload\":\"full\",\"params\":{}}",
                        "{\"x\":[true,false,null,-1.25e+3,{}]}",
                        "{\"x\":\"escaped\\n\\u1234\"}"};
  const char *bad[] = {
      "{\"x\":0,\"x\":1}", "{\"x\":1e}",      "{\"x\":01}",
      "{\"x\":-.5}",       "{\"x\":1.}",      "{\"x\":true}junk",
      "{\"x\":\"\\q\"}",   "{\"\\u0078\":1}", "[]",
      "{\"x\": [1,]}",     "{\"x\":1,}",      "{\"x\":{\"a\":1,\"a\":2}}"};
  for (size_t i = 0; i < ARRAY(good); i++)
    assert(parse(&j, good[i]));
  for (size_t i = 0; i < ARRAY(bad); i++)
    assert(!parse(&j, bad[i]));
  uint32_t random = 1337;
  char b[1024];
  for (int i = 0; i < 20000; i++) {
    random = random * 1664525U + 1013904223U;
    size_t n = random % sizeof(b);
    for (size_t x = 0; x < n; x++) {
      random = random * 1664525U + 1013904223U;
      b[x] = (char)(1 + (random % 127));
    }
    b[n] = 0;
    (void)parse(&j, b);
  }
  puts("native parser sanitizer checks passed");
  return 0;
}
