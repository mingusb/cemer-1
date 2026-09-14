/* Test the production NIfTI and compressed-file implementation locally. */
#include "../nifti1_io.h"
#include <stdint.h>

static int check_image(const char *filename, int compressed) {
  const int dimensions[8] = {3, 4, 3, 2, 1, 1, 1, 1};
  const char extension[] = "Modern stack gzip regression";
  nifti_image *original = nifti_make_new_nim(dimensions, DT_UINT16, 1);
  nifti_image *loaded = NULL;
  nifti_image *ascii_image = NULL;
  char *ascii = NULL;
  FILE *bytes = NULL;
  int result = 1;
  size_t i;
  if (!original) goto finish;
  original->dx = original->pixdim[1] = 0.7f;
  original->dy = original->pixdim[2] = 0.8f;
  original->dz = original->pixdim[3] = 1.2f;
  for (i = 0; i < original->nvox; ++i)
    ((uint16_t *)original->data)[i] = (uint16_t)(i * 17 + 3);
  if (nifti_set_filenames(original, filename, 0, 1) != 0) goto finish;
  if (nifti_add_extension(original, extension, sizeof(extension), NIFTI_ECODE_COMMENT) != 0)
    goto finish;
  nifti_image_write(original);

  /* Verify genuine gzip bytes; a matching writer/reader bug must not pass. */
  bytes = fopen(filename, "rb");
  if (!bytes) goto finish;
  if (compressed && (fgetc(bytes) != 0x1f || fgetc(bytes) != 0x8b)) goto finish;
  fclose(bytes);
  bytes = NULL;
  loaded = nifti_image_read(filename, 1);
  if (!loaded || !loaded->data || loaded->nvox != 24 ||
      loaded->nx != 4 || loaded->ny != 3 || loaded->nz != 2 ||
      loaded->datatype != DT_UINT16 ||
      fabsf(loaded->dx - 0.7f) > 1e-6f ||
      fabsf(loaded->dy - 0.8f) > 1e-6f ||
      fabsf(loaded->dz - 1.2f) > 1e-6f) goto finish;
  for (i = 0; i < loaded->nvox; ++i)
    if (((uint16_t *)loaded->data)[i] != (uint16_t)(i * 17 + 3)) goto finish;
  if (loaded->num_ext != 1 || loaded->ext_list[0].ecode != NIFTI_ECODE_COMMENT ||
      strcmp(loaded->ext_list[0].edata, extension) != 0) goto finish;
  ascii = nifti_image_to_ascii(loaded);
  if (!ascii) goto finish;
  ascii_image = nifti_image_from_ascii(ascii, NULL);
  if (!ascii_image || ascii_image->nvox != loaded->nvox ||
      ascii_image->datatype != loaded->datatype) goto finish;
  result = 0;
finish:
  if (bytes) fclose(bytes);
  free(ascii);
  if (ascii_image) nifti_image_free(ascii_image);
  if (loaded) nifti_image_free(loaded);
  if (original) nifti_image_free(original);
  if (result) fprintf(stderr, "NIfTI round trip failed: %s\n", filename);
  return result;
}

int main(int argc, char **argv) {
  char plain[4096], gzip[4096];
  int result;
  if (argc != 2 || !nifti_compiled_with_zlib()) return 2;
  if (snprintf(plain, sizeof(plain), "%s/volume.nii", argv[1]) >= (int)sizeof(plain) ||
      snprintf(gzip, sizeof(gzip), "%s/volume.nii.gz", argv[1]) >= (int)sizeof(gzip))
    return 2;
  result = check_image(plain, 0) || check_image(gzip, 1);
  if (!result) puts("NIfTI plain/gzip data, geometry, extension, and ASCII checks passed");
  return result;
}
