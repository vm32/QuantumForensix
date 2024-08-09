#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libimobiledevice/libimobiledevice.h>
#include <libimobiledevice/lockdown.h>
#include <libimobiledevice/afc.h>
#include <plist/plist.h>

#define AFC_MAX_PACKET_SIZE 4096

typedef struct {
    char *path;
    uint64_t size;
    uint64_t mtime;
} file_info_t;

idevice_t device = NULL;
lockdownd_client_t lockdown = NULL;
afc_client_t afc = NULL;

int connect_to_device() {
    if (idevice_new(&device, NULL) != IDEVICE_E_SUCCESS) {
        printf("Error: Unable to connect to device.\n");
        return -1;
    }

    if (lockdownd_client_new_with_handshake(device, &lockdown, "QuantumSleuth") != LOCKDOWN_E_SUCCESS) {
        printf("Error: Unable to establish lockdown connection.\n");
        idevice_free(device);
        return -1;
    }

    lockdownd_service_descriptor_t service = NULL;
    if (lockdownd_start_service(lockdown, "com.apple.afc", &service) != LOCKDOWN_E_SUCCESS) {
        printf("Error: Unable to start AFC service.\n");
        lockdownd_client_free(lockdown);
        idevice_free(device);
        return -1;
    }

    if (afc_client_new(device, service, &afc) != AFC_E_SUCCESS) {
        printf("Error: Unable to create AFC client.\n");
        lockdownd_client_free(lockdown);
        idevice_free(device);
        return -1;
    }

    lockdownd_service_descriptor_free(service);
    return 0;
}

void disconnect_from_device() {
    if (afc) afc_client_free(afc);
    if (lockdown) lockdownd_client_free(lockdown);
    if (device) idevice_free(device);
}

int list_directory(const char *dir_path) {
    char **list = NULL;
    if (afc_read_directory(afc, dir_path, &list) != AFC_E_SUCCESS) {
        printf("Error: Unable to read directory %s\n", dir_path);
        return -1;
    }

    int i = 0;
    while (list[i]) {
        printf("%s\n", list[i]);
        free(list[i]);
        i++;
    }
    free(list);

    return 0;
}

int get_file_info(const char *file_path, file_info_t *info) {
    char **file_info = NULL;
    if (afc_get_file_info(afc, file_path, &file_info) != AFC_E_SUCCESS) {
        printf("Error: Unable to get file info for %s\n", file_path);
        return -1;
    }

    int i;
    for (i = 0; file_info[i]; i += 2) {
        if (!strcmp(file_info[i], "st_size")) {
            info->size = strtoull(file_info[i+1], NULL, 10);
        } else if (!strcmp(file_info[i], "st_mtime")) {
            info->mtime = strtoull(file_info[i+1], NULL, 10);
        }
        free(file_info[i]);
        free(file_info[i+1]);
    }
    free(file_info);

    info->path = strdup(file_path);
    return 0;
}

int copy_file(const char *src_path, const char *dest_path) {
    uint64_t handle = 0;
    if (afc_file_open(afc, src_path, AFC_FOPEN_RDONLY, &handle) != AFC_E_SUCCESS) {
        printf("Error: Unable to open source file %s\n", src_path);
        return -1;
    }

    FILE *dest_file = fopen(dest_path, "wb");
    if (!dest_file) {
        printf("Error: Unable to open destination file %s\n", dest_path);
        afc_file_close(afc, handle);
        return -1;
    }

    char buffer[AFC_MAX_PACKET_SIZE];
    uint32_t bytes_read = 0;
    while (afc_file_read(afc, handle, buffer, sizeof(buffer), &bytes_read) == AFC_E_SUCCESS) {
        if (bytes_read == 0) break;
        fwrite(buffer, 1, bytes_read, dest_file);
    }

    afc_file_close(afc, handle);
    fclose(dest_file);
    return 0;
}

int main(int argc, char *argv[]) {
    if (connect_to_device() != 0) {
        return 1;
    }

    printf("Connected to iOS device.\n");

    // Example usage
    list_directory("/");

    file_info_t info;
    if (get_file_info("/var/mobile/Library/SMS/sms.db", &info) == 0) {
        printf("SMS database size: %llu bytes\n", info.size);
        printf("Last modified: %llu\n", info.mtime);
        free(info.path);
    }

    if (copy_file("/var/mobile/Library/SMS/sms.db", "sms_backup.db") == 0) {
        printf("SMS database copied to sms_backup.db\n");
    }

    disconnect_from_device();
    printf("Disconnected from iOS device.\n");

    return 0;
}
