import tensorflow as tf
from tensorflow.keras import datasets, layers, models
import matplotlib.pyplot as plt
from datetime import datetime

# 1. Carregar o dataset (CIFAR-10: 60000 imagens 32x32, 10 classes)
(train_images, train_labels), (test_images, test_labels) = datasets.cifar10.load_data()

# 2. Normalizar os pixels para o intervalo [0, 1]
train_images, test_images = train_images / 255.0, test_images / 255.0

class_names = ['avião', 'automóvel', 'pássaro', 'gato', 'veado',
               'cachorro', 'sapo', 'cavalo', 'navio', 'caminhão']

# 3. Construir o modelo CNN
model = models.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(32, 32, 3)),
    layers.MaxPooling2D((2, 2)),

    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),

    layers.Conv2D(64, (3, 3), activation='relu'),

    layers.Flatten(),
    layers.Dense(64, activation='relu'),
    layers.Dense(10, activation='softmax')
])

model.summary()

# 4. Compilar o modelo
model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

# 5. Treinar o modelo
history = model.fit(train_images, train_labels, epochs=10,
                     validation_data=(test_images, test_labels))

# 6. Avaliar o modelo no conjunto de teste
test_loss, test_acc = model.evaluate(test_images, test_labels, verbose=2)
print(f"\nAcurácia no teste: {test_acc:.4f}")

# 6.1 Salvar os resultados do treinamento em results.txt
with open('results.txt', 'a', encoding='utf-8') as f:
    f.write(f"===== Treinamento em {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
    f.write(f"Épocas: {len(history.history['accuracy'])}\n")
    for epoch, (acc, loss, val_acc, val_loss) in enumerate(zip(
            history.history['accuracy'],
            history.history['loss'],
            history.history['val_accuracy'],
            history.history['val_loss']), start=1):
        f.write(f"Época {epoch}: accuracy={acc:.4f} - loss={loss:.4f} - "
                f"val_accuracy={val_acc:.4f} - val_loss={val_loss:.4f}\n")
    f.write(f"Resultado final no teste: accuracy={test_acc:.4f} - loss={test_loss:.4f}\n\n")

# 7. Plotar a evolução da acurácia durante o treinamento
plt.plot(history.history['accuracy'], label='acurácia (treino)')
plt.plot(history.history['val_accuracy'], label='acurácia (validação)')
plt.xlabel('Época')
plt.ylabel('Acurácia')
plt.ylim([0, 1])
plt.legend(loc='lower right')
plt.show()

# 8. Salvar o modelo treinado
model.save('cnn_model.keras')
