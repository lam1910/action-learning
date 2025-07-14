import tensorflow as tf
import numpy as np
import os
from tensorflow.keras.models import load_model

# Load original trained model
model_fp32 = load_model("arduino_cnn_model.h5")

# Prepare representative dataset function (for calibration)
(x_train, _), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()
x_train = x_train.astype(np.float32) / 255.0
x_test = x_test.astype(np.float32) / 255.0

def representative_dataset():
    for i in range(100):
        yield [x_train[i:i+1]]

# Convert model to TFLite INT8
converter = tf.lite.TFLiteConverter.from_keras_model(model_fp32)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]

# Ensure full int8 quantization
converter.inference_input_type = tf.uint8
converter.inference_output_type = tf.uint8

# Convert
tflite_quant_model = converter.convert()

# Save directory
output_dir = "exported_models"
os.makedirs(output_dir, exist_ok=True)

# Save TFLite model
model_path = os.path.join(output_dir, "arduino_cnn_model_quant.tflite")
with open(model_path, "wb") as f:
    f.write(tflite_quant_model)

print(f"✅ Quantized model exported to: {model_path}")
