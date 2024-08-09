#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <libimobiledevice/libimobiledevice.h>
#include <libimobiledevice/lockdown.h>
#include <libimobiledevice/afc.h>
#include <libimobiledevice/file_relay.h>
#include <libimobiledevice/installation_proxy.h>
#include <plist/plist.h>
#include <openssl/evp.h>
#include <openssl/aes.h>
#include <sqlite3.h>

#define AFC_MAX_PACKET_SIZE 4096
#define MAX_FILENAME_LEN 256
#define ENCRYPTION_KEY "iOSynthesisSecretKey123"

typedef struct {
    char *path;
    uint64_t size;
    uint64_t mtime;
} file_info_t;

idevice_t device = NULL;
lockdownd_client_t lockdown = NULL;
afc_client_t afc = NULL;
char *udid = NULL;

void encrypt_file(const char *input_file, const char *output_file) {
    FILE *ifp = fopen(input_file, "rb");
    FILE *ofp = fopen(output_file, "wb");
    
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, (unsigned char*)ENCRYPTION_KEY, NULL);
    
    unsigned char inbuf[1024], outbuf[1024 + EVP_MAX_BLOCK_LENGTH];
    int inlen, outlen;
    
    while ((inlen = fread(inbuf, 1, 1024, ifp)) > 0) {
        EVP_EncryptUpdate(ctx, outbuf, &outlen, inbuf, inlen);
        fwrite(outbuf, 1, outlen, ofp);
    }
    
    EVP_EncryptFinal_ex(ctx, outbuf, &outlen);
    fwrite(outbuf, 1, outlen, ofp);
    
    EVP_CIPHER_CTX_free(ctx);
    fclose(ifp);
    fclose(ofp);
}

int connect_to_device() {
    if (idevice_new(&device, NULL) != IDEVICE_E_SUCCESS) {
        printf("Error: Unable to connect to device.\n");
        return -1;
    }

    if (lockdownd_client_new_with_handshake(device, &lockdown, "iOSynthesis") != LOCKDOWN_E_SUCCESS) {
        printf("Error: Unable to establish lockdown connection.\n");
        idevice_free(device);
        return -1;
    }

    lockdownd_get_device_udid(lockdown, &udid);

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
    if (udid) free(udid);
}

int extract_sms_messages(const char *output_file) {
    char *path = "/var/mobile/Library/SMS/sms.db";
    char local_path[MAX_FILENAME_LEN];
    snprintf(local_path, MAX_FILENAME_LEN, "%s_sms.db", udid);

    if (copy_file(path, local_path) != 0) {
        printf("Failed to copy SMS database.\n");
        return -1;
    }

    sqlite3 *db;
    if (sqlite3_open(local_path, &db) != SQLITE_OK) {
        printf("Failed to open SMS database.\n");
        return -1;
    }

    FILE *output = fopen(output_file, "w");
    if (!output) {
        printf("Failed to open output file.\n");
        sqlite3_close(db);
        return -1;
    }

    const char *sql = "SELECT datetime(message.date, 'unixepoch') as date, "
                      "handle.id as phone_number, message.text "
                      "FROM message LEFT JOIN handle ON message.handle_id = handle.ROWID "
                      "ORDER BY message.date DESC;";

    sqlite3_stmt *stmt;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        printf("Failed to prepare SQL statement.\n");
        sqlite3_close(db);
        fclose(output);
        return -1;
    }

    fprintf(output, "Date,Phone Number,Message\n");
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        fprintf(output, "%s,%s,%s\n",
                sqlite3_column_text(stmt, 0),
                sqlite3_column_text(stmt, 1),
                sqlite3_column_text(stmt, 2));
    }

    sqlite3_finalize(stmt);
    sqlite3_close(db);
    fclose(output);

    // Encrypt the output file
    char encrypted_file[MAX_FILENAME_LEN];
    snprintf(encrypted_file, MAX_FILENAME_LEN, "%s.enc", output_file);
    encrypt_file(output_file, encrypted_file);
    remove(output_file);  // Remove the unencrypted file

    printf("SMS messages extracted and encrypted to %s\n", encrypted_file);
    return 0;
}

int extract_installed_apps() {
    instproxy_client_t ipc = NULL;
    lockdownd_service_descriptor_t service = NULL;
    
    if (lockdownd_start_service(lockdown, "com.apple.mobile.installation_proxy", &service) != LOCKDOWN_E_SUCCESS) {
        printf("Error: Unable to start installation proxy service.\n");
        return -1;
    }

    if (instproxy_client_new(device, service, &ipc) != INSTPROXY_E_SUCCESS) {
        printf("Error: Unable to create installation proxy client.\n");
        lockdownd_service_descriptor_free(service);
        return -1;
    }

    plist_t client_opts = instproxy_client_options_new();
    instproxy_client_options_add(client_opts, "ApplicationType", "User", NULL);

    plist_t apps = NULL;
    if (instproxy_browse(ipc, client_opts, &apps) != INSTPROXY_E_SUCCESS) {
        printf("Error: Unable to retrieve installed apps.\n");
        instproxy_client_options_free(client_opts);
        instproxy_client_free(ipc);
        return -1;
    }

    FILE *output = fopen("installed_apps.csv", "w");
    if (!output) {
        printf("Error: Unable to open output file.\n");
        plist_free(apps);
        instproxy_client_options_free(client_opts);
        instproxy_client_free(ipc);
        return -1;
    }

    fprintf(output, "App Name,Bundle ID,Version\n");

    uint32_t i, app_count = plist_array_get_size(apps);
    for (i = 0; i < app_count; i++) {
        plist_t app = plist_array_get_item(apps, i);
        char *app_name = NULL, *bundle_id = NULL, *version = NULL;
        
        plist_t node = plist_dict_get_item(app, "CFBundleName");
        if (node) plist_get_string_val(node, &app_name);
        
        node = plist_dict_get_item(app, "CFBundleIdentifier");
        if (node) plist_get_string_val(node, &bundle_id);
        
        node = plist_dict_get_item(app, "CFBundleVersion");
        if (node) plist_get_string_val(node, &version);

        if (app_name && bundle_id && version) {
            fprintf(output, "%s,%s,%s\n", app_name, bundle_id, version);
        }

        free(app_name);
        free(bundle_id);
        free(version);
    }

    fclose(output);
    printf("Installed apps list saved to installed_apps.csv\n");

    plist_free(apps);
    instproxy_client_options_free(client_opts);
    instproxy_client_free(ipc);
    return 0;
}

void generate_report(const char *output_file) {
    FILE *report = fopen(output_file, "w");
    if (!report) {
        printf("Error: Unable to create report file.\n");
        return;
    }

    fprintf(report, "iOSynthesis Forensic Report\n");
    fprintf(report, "==========================\n\n");

    time_t now = time(NULL);
    fprintf(report, "Report generated on: %s", ctime(&now));
    fprintf(report, "Device UDID: %s\n\n", udid);

    // Add more sections to the report as needed
    fprintf(report, "1. Extracted Data\n");
    fprintf(report, "   - SMS messages: sms_messages.csv.enc\n");
    fprintf(report, "   - Installed apps: installed_apps.csv\n");
    fclose(report);
    printf("Forensic report generated: %s\n", output_file);
}

int main(int argc, char *argv[]) {
    if (connect_to_device() != 0) {
        return 1;
    }

    printf("Connected to iOS device (UDID: %s).\n", udid);
    extract_sms_messages("sms_messages.csv");
    extract_installed_apps();
    generate_report("forensic_report.txt");

    disconnect_from_device();
    printf("Disconnected from iOS device.\n");

    return 0;
}
