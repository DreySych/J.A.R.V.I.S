from ru_normalizr import NormalizeOptions, Normalizer

_normalizer = Normalizer(NormalizeOptions.tts())


def normalize_for_tts(text):
    if not text or not text.strip():
        return text

    return _normalizer.normalize(text)
