#include "xbeParse.h"
#include <xtl.h>  // XDK types like FILE, fopen, fread
#include <stdio.h>
#include <string.h>

bool parseXBE(const char* filepath, char* titleNameOut, uint32_t* titleIdOut) {
    FILE* file = fopen(filepath, "rb");
    if (!file)
        return false;

    // Read first 8192 bytes to ensure we cover the cert even if offset is deep
    uint8_t xbeData[8192];
    size_t bytesRead = fread(xbeData, 1, sizeof(xbeData), file);
    if (bytesRead < sizeof(XBEHeader)) {
        fclose(file);
        return false;
    }

    // Validate magic
    XBEHeader* header = (XBEHeader*)xbeData;
    if (header->magic != XBE_MAGIC) {
        fclose(file);
        return false;
    }

    // Get offset to cert
    uint32_t certOffset = header->certificate_address - header->base_address;
    if (certOffset + sizeof(XBECertificate) > bytesRead) {
        fclose(file);
        return false;
    }

    XBECertificate* cert = (XBECertificate*)(xbeData + certOffset);

    // Extract title ID
    if (titleIdOut)
        *titleIdOut = cert->title_id;

    // Extract and convert title name
    if (titleNameOut) {
        for (int i = 0; i < 40; ++i) {
            uint16_t wc = cert->title_name[i];
            if (wc == 0) {
                titleNameOut[i] = '\0';
                break;
            }

            // Fallback for non-printable chars
            titleNameOut[i] = (wc >= 0x20 && wc <= 0x7E) ? (char)wc : '?';
            titleNameOut[i + 1] = '\0';
        }
    }

    fclose(file);
    return true;
}
