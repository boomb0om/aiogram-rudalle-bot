from aiogram import types

KEYBOARDS = {
    'hide': types.ReplyKeyboardRemove(selective=False),
    'imgs_to_gen_full': {
        'variants': ['20', '24', '32', '36'],
        'markup': None,
    },
    'imgs_to_gen_medium': {
        'variants': ['12', '16', '20', '24'],
        'markup': None,
    },
    'imgs_to_gen_small': {
        'variants': ['6', '9', '12'],
        'markup': None,
    },
    'aspect_ratio': {
        'variants': ['16:9', '4:3', '1:1', '3:4', '9:16'],
        'markup': None,
    },
}

### Create keyboard markups
# imgs_to_gen_full
markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
markup.row(*[types.KeyboardButton(variant) for variant in KEYBOARDS['imgs_to_gen_full']['variants'][:3]])
markup.row(*[types.KeyboardButton(variant) for variant in KEYBOARDS['imgs_to_gen_full']['variants'][3:]])
KEYBOARDS['imgs_to_gen_full']['markup'] = markup

# imgs_to_gen_medium
markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
markup.row(*[types.KeyboardButton(variant) for variant in KEYBOARDS['imgs_to_gen_medium']['variants']])
KEYBOARDS['imgs_to_gen_medium']['markup'] = markup

# imgs_to_gen_small
markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
markup.row(*[types.KeyboardButton(variant) for variant in KEYBOARDS['imgs_to_gen_small']['variants']])
KEYBOARDS['imgs_to_gen_small']['markup'] = markup

# aspect_ratio
markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
markup.row(*[types.KeyboardButton(variant) for variant in KEYBOARDS['aspect_ratio']['variants']])
KEYBOARDS['aspect_ratio']['markup'] = markup