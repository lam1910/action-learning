import os
 
fp32_size = os.path.getsize("arduino_cnn_model.h5") / 1024  # in KB
int8_size = os.path.getsize("arduino_cnn_model_quant.tflite") / 1024  # in KB
 
print(f"Original Model Size: {fp32_size:.2f} KB")
print(f"Quantized Model Size: {int8_size:.2f} KB")
print(f"Compression Ratio: {fp32_size / int8_size:.2f}x")