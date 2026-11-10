"""Design token checks: presence, legacy aliases and WCAG contrast."""

import re
from pathlib import Path

import pytest

CSS_PATH = Path(__file__).resolve().parent.parent / 'app/static/css/core/variables.css'
SELECTORS = {'light': ':root', 'dark': 'html[data-theme="dark"]'}

TEXT_PAIRS = [
    ('--color-text', '--color-bg'),
    ('--color-text', '--color-surface'),
    ('--color-text', '--color-surface-2'),
    ('--color-text-muted', '--color-bg'),
    ('--color-text-muted', '--color-surface'),
    ('--color-text-subtle', '--color-bg'),
    ('--color-text-subtle', '--color-surface'),
    ('--color-primary', '--color-surface'),
    ('--color-primary', '--color-bg'),
    ('--color-on-primary', '--color-primary'),
    ('--color-success', '--color-surface'),
    ('--color-warning', '--color-surface'),
    ('--color-danger', '--color-surface'),
]

LEGACY = [
    '--bg-color-primary', '--bg-color-secondary', '--bg-color-tertiary',
    '--card-bg', '--text-color-primary', '--text-color',
    '--text-color-secondary', '--text-color-tertiary', '--muted-color',
    '--text-muted', '--border-color', '--primary-color', '--accent-color',
    '--box-shadow', '--sidebar-bg', '--sidebar-text', '--sidebar-hover',
]

NON_COLOUR_TOKENS = [
    '--font-sans', '--font-mono',
    '--text-xs', '--text-sm', '--text-base', '--text-lg', '--text-xl', '--text-2xl',
    '--space-1', '--space-2', '--space-3', '--space-4',
    '--space-5', '--space-6', '--space-7', '--space-8',
    '--radius-sm', '--radius-md', '--radius-lg', '--radius-full',
    '--shadow-1', '--shadow-2',
    '--sidebar-width', '--sidebar-width-collapsed',
    '--bottom-nav-height', '--header-height',
]


def parse_block(css, selector):
    """Return {custom-property: value} for the first rule with this selector."""
    match = re.search(re.escape(selector) + r'\s*\{([^}]*)\}', css)
    assert match, f'no rule for {selector}'
    return {
        name: value.strip()
        for name, value in re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', match.group(1))
    }


def _luminance(hex_colour):
    hex_colour = hex_colour.lstrip('#')
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(hex_a, hex_b):
    lighter, darker = sorted((_luminance(hex_a), _luminance(hex_b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.fixture(scope='module')
def css():
    return CSS_PATH.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def themes(css):
    light = parse_block(css, SELECTORS['light'])
    dark = {**light, **parse_block(css, SELECTORS['dark'])}
    return {'light': light, 'dark': dark}


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('fg,bg', TEXT_PAIRS)
def test_text_contrast_meets_aa(themes, theme, fg, bg):
    tokens = themes[theme]
    ratio = contrast(tokens[fg], tokens[bg])
    assert ratio >= 4.5, f'{theme}: {fg} on {bg} is {ratio:.2f}:1'


def test_text_on_accent_fill_is_readable(themes):
    light, dark = themes['light'], themes['dark']
    assert contrast(light['--color-text'], light['--color-accent']) >= 4.5
    assert contrast(dark['--color-bg'], dark['--color-accent']) >= 4.5


@pytest.mark.parametrize('name', LEGACY)
def test_legacy_alias_points_at_new_token(themes, name):
    assert themes['light'][name].startswith('var(--')


def test_removed_tokens_are_gone(css):
    assert '--dashboard-gradient' not in css
    assert '--dashboard-shape' not in css


def test_dark_block_defines_every_colour_token(css):
    light = parse_block(css, SELECTORS['light'])
    dark = parse_block(css, SELECTORS['dark'])
    light_colours = {name for name in light if name.startswith('--color-')}
    assert light_colours == set(dark)


@pytest.mark.parametrize('name', NON_COLOUR_TOKENS)
def test_scale_token_is_defined(themes, name):
    assert name in themes['light']
