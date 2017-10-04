"""Training script for referring relationships.
"""

from keras import backend as K
from keras.callbacks import ModelCheckpoint
from keras.callbacks import TensorBoard
from keras.optimizers import Adam

from config import parse_args
from iterator import RefRelDataIterator
from model import ReferringRelationshipsModel
from utils.eval_utils import iou_acc_3, iou_3
from utils.train_utils import format_args, get_dir_name, format_history, get_opt

import json
import logging
import numpy as np
import os


if __name__=='__main__':
    # Parse command line arguments.
    args = parse_args()

    # First check if --use-models-dir is set. In that case, create a new folder
    # to store all the training logs.
    if (args.use_models_dir and
        args.models_dir is not None and
        args.save_dir is None):
        args.save_dir = get_dir_name(args.models_dir)

    # If the save directory does exists, don't launch the training script.
    if os.path.exists(args.save_dir):
        print('The directory %s already exists. Exiting training!'
              % args.save_dir)

    # Otherwise, create the directory and start training.
    os.mkdir(args.save_dir)

    # Setup logging.
    logfile = os.path.join(args.save_dir, 'train.log')
    logging.basicConfig(level=logging.INFO, filename=logfile)

    # Store the arguments used in this training process.
    args_file = open(os.path.join(args.save_dir, 'args.json'), 'w')
    json.dump(args.__dict__, args_file)
    args_file.close()
    logging.info(format_args(args))

    # Setup the training and validation data iterators
    train_generator = RefRelDataIterator(args.image_data_dir, args.train_data_dir,
                                         input_dim=args.input_dim,
                                         batch_size=args.batch_size)
    val_generator = RefRelDataIterator(args.image_data_dir, args.val_data_dir,
                                       input_dim=args.input_dim,
                                       batch_size=args.batch_size)
    logging.info('Train on {} samples'.format(train_generator.samples))
    logging.info('Validate on {} samples'.format(val_generator.samples))


    # Start training
    relationships_model = ReferringRelationshipsModel(args)
    model = relationships_model.build_model()
    model.summary(print_fn=lambda x: logging.info(x + '\n'))
    optimizer = get_opt(opt=args.opt, lr=args.lr, lr_decay=args.lr_decay)
    model.compile(loss=['binary_crossentropy', 'binary_crossentropy'],
                  optimizer=optimizer,
                  metrics=[iou_acc_3, iou_3])
    tb_callback = TensorBoard(log_dir=args.save_dir)
    checkpointer = ModelCheckpoint(
        filepath=os.path.join(
            args.save_dir, 'model{epoch:02d}-{val_loss:.2f}.h5'),
        verbose=1,
        save_best_only=args.save_best_only,
        monitor='val_loss')
    history = model.fit_generator(train_generator,
                                  steps_per_epoch=int(train_generator.samples/args.batch_size),
                                  epochs=args.epochs,
                                  validation_data=val_generator,
                                  validation_steps=int(val_generator.samples/args.batch_size),
                                  callbacks=[checkpointer, tb_callback]).history
    logging.info(format_history(history, args.epochs))
    logging.info('Best validation loss: {}'.format(round(np.min(history['val_loss']), 4)))
