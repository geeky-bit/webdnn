from typing import List

import numpy as np

from webdnn.backend.code_generator.allocator import MemoryLayout
from webdnn.backend.code_generator.injectors.kernel_name_injector import KernelNameInjector
from webdnn.backend.code_generator.injectors.buffer_injector import MetaInjector
from webdnn.backend.webassembly.kernel import Kernel
from webdnn.graph.operators.concat import Concat

template = """
void %%FUNC_NAME%%(const int * %%META_NAME%%)
{
    float *y = data_buffer + %%META_LOAD(concat_y_offset)%%;
    const int N = %%META_LOAD(concat_N)%%;
    const int D = %%META_LOAD(concat_D)%%;
    const int *x_offsets = &(%%META_LOAD(concat_x_offsets)%%);
    const int *y_offsets = &(%%META_LOAD(concat_y_offsets)%%);
    const int *x_shapes = &(%%META_LOAD(concat_x_shapes)%%);
    const int *x_strides_in_y = &(%%META_LOAD(concat_x_strides_in_y)%%);
    
    int x_index = 0;
    
    for (int n = 0; n < N; n++) {
        const float *x = data_buffer + x_offsets[n];
        const int y_offset = y_offsets[n];
        const int *x_shape = &(x_shapes[n*D]);
        const int *x_stride_in_y = &(x_strides_in_y[n*D]);
        
        int x_size = 1;
        for (int d = 0; d < D; d++) {
            x_size *= x_shape[d];
        }
        
        while (x_index < x_size) { 
            int y_index = y_offset;
            int s = x_index;
            for (int d = D-1; d >= 0; d--) {
                y_index += x_stride_in_y[d] * (s % x_shape[d]);
                s /= x_shape[d];
            }
        
            y[y_index] = x[x_index];
            
            x_index++;
        }
        
        x_index -= x_size;
    }
}
"""


# noinspection PyUnusedLocal
def concat(op: Concat, memory_layout: MemoryLayout) -> List[Kernel]:
    xs = [memory_layout[op.inputs[f"x{str(i)}"]] for i in range(len(op.inputs))]
    y = memory_layout[op.outputs["y"]]
    target_axis = op.axis

    x_offsets = [x.offset for x in xs]
    x_shapes = [x.variable.shape for x in xs]

    y_strides = []
    stride = 1
    for s in reversed(y.variable.shape):
        y_strides.insert(0, stride)
        stride *= s

    # x_strides[i][j] is stride size of xs[i].order.axes[j] in y
    x_strides_in_y = [[] for _ in xs]
    for x, strides in zip(xs, x_strides_in_y):
        for axis in x.variable.order.axes:
            strides.append(y_strides[y.variable.order.axes_dict[axis]])

    # x_offsets[i] is memory offset of xs[i]'s data in y.
    y_offsets = []
    target_axis_offset = 0
    for x in xs:
        y_offsets.append(target_axis_offset * y_strides[y.variable.order.axes_dict[target_axis]])
        target_axis_offset += x.variable.shape_dict[target_axis]

    meta_injector = MetaInjector()
    meta_injector.register({
        "concat_y_offset": y.offset,
        "concat_D": len(y.variable.shape),
        "concat_N": len(xs),
        "concat_x_offsets": np.array(x_offsets, dtype=np.int32).tobytes(),
        "concat_x_strides_in_y": np.array(x_strides_in_y, dtype=np.int32).tobytes(),
        "concat_x_shapes": np.array(x_shapes, dtype=np.int32).tobytes(),
        "concat_y_offsets": np.array(y_offsets, dtype=np.int32).tobytes(),
    })

    name_injector = KernelNameInjector(op)

    source = template
    source = meta_injector.inject(source)
    source = name_injector.inject(source)

    kernel = Kernel(
        {name_injector.name: source},
        name_injector.name,
        meta_injector.buffer
    )

    return [kernel]
