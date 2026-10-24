import zipfile

from constance import config

BadZipFile = zipfile.BadZipFile
ZIP_DEFLATED = zipfile.ZIP_DEFLATED
ZIP_STORED = zipfile.ZIP_STORED


def _metadata_encoding():
    enc = config.SOPDS_ZIPCODEPAGE
    if enc and enc.lower() not in ('utf-8', 'utf8'):
        return enc
    return None


def ZipFile(file, mode='r', compression=zipfile.ZIP_STORED, allowZip64=True):
    metadata_encoding = _metadata_encoding() if mode == 'r' else None
    return zipfile.ZipFile(
        file,
        mode,
        compression,
        allowZip64,
        metadata_encoding=metadata_encoding,
    )
