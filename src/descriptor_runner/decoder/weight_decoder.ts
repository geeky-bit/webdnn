///<reference path="./weight_decoder_raw.ts" />

namespace WebDNN {
    export interface PlaceHolder {
        eval: string
    }

    export interface WeightDecoder {
        decode(data: Uint8Array, memory_layout: MemoryLayout): Promise<Float32Array>;
    }

    export interface MemoryLayout {
        'static': {
            size: number,
            allocations: {
                [index: string]: {
                    name: string,
                    offset: number,
                    size: number
                }
            }
        },
        dynamic: {
            size: number | PlaceHolder,
            allocations: {
                [index: string]: {
                    name: string,
                    offset: number | PlaceHolder,
                    size: number | PlaceHolder
                }
            }
        }
    }
}
