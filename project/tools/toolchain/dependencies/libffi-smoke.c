#include <ffi.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static void require(int condition, const char *message)
{
  if (!condition) {
    fprintf(stderr, "libffi ABI check failed: %s\n", message);
    exit(EXIT_FAILURE);
  }
}

static int64_t sum_eight(int64_t a, int64_t b, int64_t c, int64_t d,
                         int64_t e, int64_t f, int64_t g, int64_t h)
{
  return a + b + c + d + e + f + g + h;
}

struct mixed_result {
  double number;
  int tag;
};

static struct mixed_result transform(struct mixed_result input, double scale)
{
  return (struct mixed_result){input.number * scale, input.tag + 1};
}

static double sum_variadic(int count, ...)
{
  va_list arguments;
  va_start(arguments, count);
  double sum = 0.0;
  for (int i = 0; i < count; ++i)
    sum += va_arg(arguments, double);
  va_end(arguments);
  return sum;
}

static void closure_add(ffi_cif *cif, void *result, void **arguments, void *data)
{
  (void)cif;
  *(double *)result = *(double *)arguments[0] + *(double *)data;
}

int main(void)
{
  ffi_cif cif;
  ffi_type *integer_types[8];
  int64_t integers[8] = {1, 2, 3, 4, 5, 6, 7, INT64_C(0x100000000)};
  void *integer_arguments[8];
  for (size_t i = 0; i < 8; ++i) {
    integer_types[i] = &ffi_type_sint64;
    integer_arguments[i] = &integers[i];
  }
  require(ffi_prep_cif(&cif, FFI_DEFAULT_ABI, 8, &ffi_type_sint64,
                      integer_types) == FFI_OK, "integer cif");
  int64_t integer_result = 0;
  ffi_call(&cif, FFI_FN(sum_eight), &integer_result, integer_arguments);
  require(integer_result == INT64_C(0x10000001c), "register and stack integers");

  ffi_type *fields[] = {&ffi_type_double, &ffi_type_sint, NULL};
  ffi_type mixed_type = {0, 0, FFI_TYPE_STRUCT, fields};
  ffi_type *mixed_arguments[] = {&mixed_type, &ffi_type_double};
  require(ffi_prep_cif(&cif, FFI_DEFAULT_ABI, 2, &mixed_type,
                      mixed_arguments) == FFI_OK, "mixed struct cif");
  struct mixed_result input = {1.25, 41};
  struct mixed_result output = {0.0, 0};
  double scale = 2.0;
  void *mixed_values[] = {&input, &scale};
  ffi_call(&cif, FFI_FN(transform), &output, mixed_values);
  require(output.number == 2.5 && output.tag == 42, "mixed struct argument/return");
  require(mixed_type.size == sizeof(struct mixed_result), "struct layout");

  ffi_type *var_types[] = {&ffi_type_sint, &ffi_type_double,
                           &ffi_type_double, &ffi_type_double};
  require(ffi_prep_cif_var(&cif, FFI_DEFAULT_ABI, 1, 4, &ffi_type_double,
                          var_types) == FFI_OK, "variadic cif");
  int count = 3;
  double values[] = {0.5, 1.25, 2.0};
  void *var_values[] = {&count, &values[0], &values[1], &values[2]};
  double var_result = 0.0;
  ffi_call(&cif, FFI_FN(sum_variadic), &var_result, var_values);
  require(var_result == 3.75, "variadic floating point arguments");

  ffi_type *closure_types[] = {&ffi_type_double};
  require(ffi_prep_cif(&cif, FFI_DEFAULT_ABI, 1, &ffi_type_double,
                      closure_types) == FFI_OK, "closure cif");
  void *code = NULL;
  ffi_closure *closure = ffi_closure_alloc(sizeof(*closure), &code);
  require(closure != NULL, "closure allocation");
  double offset = 4.25;
  require(ffi_prep_closure_loc(closure, &cif, closure_add, &offset, code) == FFI_OK,
          "closure preparation");
  double (*call_closure)(double) = (double (*)(double))code;
  require(call_closure(1.5) == 5.75, "closure call and user data");
  ffi_closure_free(closure);

  puts("libffi integer/stack, mixed struct, variadic and closure ABI checks passed");
  return EXIT_SUCCESS;
}
