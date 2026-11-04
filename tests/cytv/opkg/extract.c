/* Thin entry point into unmodified opkg 0.1.8, not an extraction model. */
#include <stdio.h>
#include <string.h>
#include "libopkg/pkg.h"
#include "libopkg/pkg_extract.h"
#include "libopkg/opkg_message.h"

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    opkg_conf_t config;
    memset(&config, 0, sizeof(config));
    config.verbosity = 1;
    conf = &config;
    pkg_t package;
    memset(&package, 0, sizeof(package));
    package.local_filename = argv[1];
    int result = pkg_extract_data_files_to_dir(&package, argv[2]);
    print_error_list();
    return result ? 1 : 0;
}
