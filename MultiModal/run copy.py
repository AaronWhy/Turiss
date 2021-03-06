import pandas as pd
import numpy as np

import tensorflow as tf
import tensorflow_hub as hub

from tensorflow import keras
from tensorflow.keras.models import Model 
from tensorflow.keras.optimizers import Adam

import argparse


def DataFrameToDataset(df):
    convert = lambda s : (list(map(int, s[1:-1].split(','))))

    df['input_ids'] = df['input_ids'].apply(convert)
    df['input_masks'] = df['input_masks'].apply(convert)
    df['input_segments'] = df['input_segments'].apply(convert)

    df['Score'] = df['Score'] - 1
    df['NormalizedHelpfulness'] = df['NormalizedHelpfulness'] - 1

    df1 = df[
        'Normalized_Product_ID',
        'Normalized_User_ID',
        'Normalized_Time_ID',
        'input_ids',
        'input_masks',
        'input_segments'
    ].copy()

    return X, Y


def DataFrameToTensor(df):
    convert = lambda s : (list(map(int, s[1:-1].split(','))))
    X = [tf.convert_to_tensor(df['Normalized_Product_ID'], dtype=tf.int32),
        tf.convert_to_tensor(df['Normalized_User_ID'], dtype=tf.int32),
        tf.convert_to_tensor(df['Normalized_Time_ID'], dtype=tf.int32),
        tf.convert_to_tensor(df['input_ids'].apply(convert), dtype=tf.int32),
        tf.convert_to_tensor(df['input_masks'].apply(convert), dtype=tf.int32),
        tf.convert_to_tensor(df['input_segments'].apply(convert), dtype=tf.int32),
    ]
    Y = [tf.convert_to_tensor(df['Score'] - 1, dtype=tf.int32),
        tf.convert_to_tensor(df['NormalizedHelpfulness'] - 1, dtype=tf.int32),
    ]
    return X, Y

def MultiModalModel():
    max_len = 128
    vocab_size = 1000
    word_dim = 64

    input_id = tf.keras.layers.Input(shape=(max_len,), dtype=tf.int32, name='input_ID')
    input_mask = tf.keras.layers.Input(shape=(max_len,), dtype=tf.int32, name = 'input_mask')
    input_segment = tf.keras.layers.Input(shape=(max_len,), dtype=tf.int32, name = 'input_seqment')

    bert_layer = hub.KerasLayer("../bert_layer", trainable=True)
    pooled_output, _ = bert_layer([input_id, input_mask, input_segment])

    input1 = keras.Input(shape=(1,), dtype=tf.float32, name='Product_ID')
    e1 = keras.layers.Embedding(vocab_size, word_dim, embeddings_initializer=tf.random_normal_initializer)(
        input1)

    input2 = keras.Input(shape=(1,), dtype=tf.float32, name='User_ID')
    e2 = keras.layers.Embedding(vocab_size, word_dim, embeddings_initializer=tf.random_normal_initializer)(
        input2)

    input3 = keras.Input(shape=(1,), dtype=tf.float32, name='Time_ID')
    e3 = keras.layers.Embedding(vocab_size, word_dim, embeddings_initializer=tf.random_normal_initializer)(
        input3)
    
    merge1 = keras.layers.Flatten()(keras.layers.concatenate([e1, e2, e3]))
    merge2 = keras.layers.concatenate([merge1, pooled_output])

    a1 = keras.layers.Dense(64, activation='relu')(merge2)
    a2 = keras.layers.Dropout(0.2)(a1)
    a3 = keras.layers.Dense(5, activation='softmax', name='Score')(a2)

    b1 = keras.layers.Dense(64, activation='relu')(merge2)
    b2 = keras.layers.Dropout(0.2)(b1)
    b3 = keras.layers.Dense(5, activation='softmax', name = 'Helpfulness')(b2)

    opt = Adam(lr=1e-5)
    model = keras.Model(inputs=[input1, input2, input3, input_id, input_mask, input_segment], \
        outputs=[a3, b3])
    model.compile(loss='sparse_categorical_crossentropy', optimizer=opt, metrics=['accuracy'])

    model.summary()
    return model


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--load', default=None
    )
    parser.add_argument(
        '--big', default=None
    )
    parser.add_argument(
        '--epoch', type=int
    )
    args = parser.parse_args()
    print(args)

    if args.big != None:
        trainset = pd.read_csv('./data/train_set.csv')
        testset = pd.read_csv('./data/test_set.csv')
    else:
        trainset = pd.read_csv('./data/local_train_set.csv')
        testset = pd.read_csv('./data/local_test_set.csv')

    train_X, train_Y = DatasetToTensor(trainset)
    test_X, test_Y = DatasetToTensor(testset)

    print(type(train_X + train_Y))
    print(len(train_X + train_Y))
    print(type(train_Y[0])

    dataset = tf.data.Dataset.from_tensor_slices(train_X + train_Y)
    for data in dataset:
        print(type(data))
        break

    exit(0)

    model = MultiModalModel()

    checkpoints_dir = './checkpoints/'
    load_file = 'bert_model.h5'

    if args.load != None:
        model.load_weights(checkpoints_dir+load_file)

    history = model.fit(x=train_X, y=train_Y, epochs = args.epoch, validation_data = (test_X, test_Y), shuffle='steps_per_epoch')

    score_preds, helpfulness_preds = model.predict(test_X)
    score_preds = score_preds.argmax(1)
    helpfulness_preds = helpfulness_preds.argmax(1)

    testset['score_preds'] = score_preds + 1
    testset['helpfulness_preds'] = helpfulness_preds + 1

    testset.to_csv(r'res.csv', index=False)

    model.save_weights(checkpoints_dir + 'bert_model.h5')







