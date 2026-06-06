"""Manual placement knobs for compressor scheduling.

All compressor_override columns are 1-based (visual columns, like your TXT/PDF).
All stages are 0-based.
"""

phase32_start_stage = {
    16: 99,
}


auto_use_c22_by_default = {
    16: False,
}


compressor_override = {
    16: {
        "wallace16_n3_5": {
            0: {
                18: [3],
            },
            1: {
                16: [3],
                17: [3],
                20: [3],
            },
            2: {
                14: [3],
                22: [3],
            },
            3: {
                4: [3],
                13: [3],
                14: [3],
                15: [3],
                16: [3],
                17: [3],
                18: [3],
                19: [3],
                20: [3],
                22: [3],
                26: [3],
                28: [3],
                30: [3],
            },
            4: {
                3: [3],
                4: [2],
                5: [2],
                6: [3],
                8: [3],
                10: [3],
                12: [3],
                13: [3],
                14: [3],
                15: [3],
                16: [2],
                17: [3],
                18: [2],
                19: [3],
                20: [3],
                21: [2],
                22: [3],
                23: [3],
                24: [3],
                25: [2],
                26: [2],
                27: [3],
                28: [2],
                29: [3],
                30: [2],
                31: [3],
            },
        }
    }
}
