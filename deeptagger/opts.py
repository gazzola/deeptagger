def general_opts(parser):
    group = parser.add_argument_group('general')
    # Output
    group.add_argument('-o', '--output-dir',
                       type=str,
                       help='Output files for this run under this dir. '
                            'If not specified, it will create a timestamp dir '
                            'inside `runs` dir.')

    # Data processing options
    group = parser.add_argument_group('random')
    group.add_argument('--seed',
                       type=int,
                       default=42,
                       help='Random seed')

    # Cuda
    group = parser.add_argument_group('gpu')
    group.add_argument('--gpu-id',
                       default=None,
                       type=int,
                       help='Use CUDA on the listed devices')
    # Logging
    group = parser.add_argument_group('logging')
    group.add_argument('--debug',
                       action='store_true',
                       help='Debug mode.')

    # Save and load
    group = parser.add_argument_group('save-load')
    group.add_argument('--save-model',
                       type=str,
                       default='',
                       help='Output dir for saving the model')
    group.add_argument('--load-model',
                       type=str,
                       default='',
                       help='Input File for loading the model')


def preprocess_opts(parser):
    # Data options
    group = parser.add_argument_group('data')

    group.add_argument('--train-path',
                       type=str,
                       help='Path to training file')
    group.add_argument('--dev-path',
                       type=str,
                       help='Path to validation file')
    group.add_argument('--test-path',
                       type=str,
                       help='Path to validation file')
    group.add_argument('--del-word',
                       type=str,
                       default=' ',
                       help='Delimiter token to split sentence tokens')
    group.add_argument('--del-tag',
                       type=str,
                       default='_',
                       help='Delimiter token to split '
                            'word tokens from  tag tokens')

    # Truncation options
    group = parser.add_argument_group('data-pruning')
    group.add_argument('--max-length',
                       type=int,
                       default=float("inf"),
                       help='Maximum sequence length')
    group.add_argument('--min-length',
                       type=int,
                       default=0,
                       help='Minimum sequence length.')

    # Dictionary options
    group = parser.add_argument_group('data-vocabulary')
    group.add_argument('--vocab-path',
                       type=str,
                       help='Path to an existing vocabulary. '
                            'Format: one word per line.')
    group.add_argument('--vocab-size',
                       type=int,
                       default=None,
                       help='Size of the vocabulary.')
    group.add_argument('--vocab-min-frequency',
                       type=int,
                       default=1,
                       help='Min word frequency for vocabulary.')

    group.add_argument('--keep-rare-with-vectors',
                       action='store_true',
                       help='Keep words that occur less then min-frequency '
                            'but are in embeddings vocabulary.')
    group.add_argument('--add-embeddings-vocab',
                       action='store_true',
                       help='Add words from embeddings vocabulary to '
                            'source/target vocabulary.')

    # Embeddings options
    group = parser.add_argument_group('data-embeddings')
    group.add_argument('--embeddings-format',
                       type=str,
                       default=None,
                       choices=['polyglot', 'word2vec', 'fasttext', 'glove'],
                       help='Word embeddings format. '
                            'See README for specific formatting instructions.')
    group.add_argument('--embeddings-path',
                       type=str,
                       help='Path to word embeddings file for source.')


def model_opts(parser):
    # Embedding Options
    pass


def train_opts(parser):
    # Training loop options
    group = parser.add_argument_group('training')
    group.add_argument('--epochs',
                       type=int,
                       default=10,
                       help='Number of epochs for training.')
    group.add_argument('--shuffle',
                       action='store_true',
                       help='Shuffle train data before each epoch.')
    group.add_argument('--train-batch-size',
                       type=int,
                       default=64,
                       help='Maximum batch size for training.')
    group.add_argument('--dev-batch-size',
                       type=int,
                       default=64,
                       help='Maximum batch size for evaluating.')
    group.add_argument('--save-checkpoint-epochs',
                       type=int,
                       default=1,
                       help='Save a checkpoint every X epochs.')

    # Optimization options
    group = parser.add_argument_group('training-optimization')
    group.add_argument('--optimizer',
                       default='sgd', choices=[
                           'sgd', 'adagrad', 'adadelta', 'adam', 'sparseadam'],
                       help='Optimization method.')
    group.add_argument('--learning-rate',
                       type=float,
                       default=1.0,
                       help='Starting learning rate. '
                            'Recommended settings: sgd = 1, adagrad = 0.1, '
                            'adadelta = 1, adam = 0.001')
