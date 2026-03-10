import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, Input

def create_dummy_model():
    # Define input shapes (256x256 RGB images)
    input_mri = Input(shape=(256, 256, 3), name='mri_input')
    input_pet = Input(shape=(256, 256, 3), name='pet_input')

    # Simple feature extraction for MRI
    x1 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(input_mri)
    x1 = layers.MaxPooling2D((2, 2))(x1)
    
    # Simple feature extraction for PET
    x2 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(input_pet)
    x2 = layers.MaxPooling2D((2, 2))(x2)

    # Fusion (Concatenation)
    concatenated = layers.Concatenate()([x1, x2])
    
    # Fusion processing
    f = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(concatenated)
    f = layers.UpSampling2D((2, 2))(f)
    
    # Output reconstruction
    output = layers.Conv2D(3, (3, 3), activation='sigmoid', padding='same', name='fused_output')(f)

    # Create model
    model = models.Model(inputs=[input_mri, input_pet], outputs=output)
    
    # Compile (dummy compilation, not needed for inference but good practice)
    model.compile(optimizer='adam', loss='mse')
    
    # Summary
    model.summary()

    # Save model
    save_path = os.path.join(os.getcwd(), 'backend', 'models', 'best_fusion_model.keras')
    model.save(save_path)
    print(f"Model saved to {save_path}")

if __name__ == "__main__":
    create_dummy_model()
