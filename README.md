# Y2K Collage Poster

Transform one or more photos into layered Y2K and millennium-futurist collage posters.

This skill preserves recognizable people, clothing, poses, objects, and relationships while reinterpreting the source material through bold cropping, repetition, scale contrast, retro-digital framing, expressive typography, and imagined turn-of-the-millennium futures.

## Features

- Works with one or multiple source photos
- Preserves recognizable faces, hairstyles, outfits, poses, props, and objects
- Automatically evaluates image quality and builds a clear visual hierarchy
- Uses repetition, detail crops, interface frames, texture, and scale contrast
- Selects a suitable aspect ratio when none is specified
- Supports exact user-supplied poster text
- Keeps layered compositions readable at thumbnail size
- Checks identity, hierarchy, typography, color, and style consistency before returning the result

## Style Families

The skill selects one primary style based on the supplied images and requested mood.

### Pop Scrapbook

Colorful editorial collage, bold posing, paper graphics, portrait cards, labels, and playful pop energy.

### Webcore Desktop

Early-internet interfaces, browser windows, media players, cursors, pixel textures, and personal digital-diary aesthetics.

### Punk Halftone

Xerox grain, coarse halftones, duotone portraits, distressed typography, and confrontational print-zine energy.

### Liquid Chrome Futurism

Reflective metal, fluid chrome forms, cold highlights, glass accents, and machine-organic futuristic surfaces.

A supporting style may be added when it serves a specific compositional purpose without competing with the primary style.

## Installation

Download or clone this repository, then copy the `y2k-collage-poster-v1` folder into the skills directory supported by your agent.

For Codex, the default personal skills directory is:

```text
~/.codex/skills/
```

Restart or reload your agent if required.

## Usage

Supply one or more photos and ask your agent to use the skill.

### Basic Example

```text
Use y2k-collage-poster-v1 to transform these photos into a Y2K collage poster.
```

### Directed Example

```text
Use y2k-collage-poster-v1 to create a 3:4 vertical Webcore poster.

Use the first photo as the main subject and the other photos as smaller
repeated frames. Preserve the subject's face, hairstyle, clothing, and
headphones. Use silver, icy blue, and acid green.

The title must read: "SIGNAL LOST"
```

You may specify:

- Aspect ratio or orientation
- Primary and must-use photos
- Preferred style family
- Color palette
- Exact poster text
- Important facial, clothing, pose, or object details

If these choices are omitted, the skill determines them from the supplied images.

### Recommended Workflow

For best results, start by giving the source images directly to the agent with a simple request. Let the agent inspect the images and determine the strongest subject, visual hierarchy, style route, palette, material system, and composition from the source itself.

Add only the constraints that genuinely matter, such as a required aspect ratio, must-use image, or exact poster text. Stacking too many style tags, motifs, colors, layout instructions, and decorative requirements can create prompt pollution, weaken source fidelity, and make the final composition less coherent.

## Creative Approach

The skill treats Y2K as an imagined future rather than a collection of decorative stickers.

Each poster is built around:

1. A recognizable source identity
2. A clear visual hierarchy
3. A source-responsive future premise
4. One dominant material and color system
5. Repetition, cropping, overlap, and scale contrast
6. A readable path through the composition

The result remains visibly constructed as a collage instead of becoming a generic science-fiction scene.

## Image Handling

The skill inspects every supplied image before generation.

Stronger images may become the main subject, while lower-resolution images may appear as smaller cards, halftone fragments, interface replays, or background textures. User-designated must-use images are preserved.

With a single source image, the skill creates variety through truthful crops and visual treatments. It does not invent alternate outfits, poses, or events and present them as source material.

The skill does not infer personal names, relationships, locations, brands, dates, or biographical information from supplied images.

## Requirements

A compatible agent with:

- Support for loading skill instructions
- Access to supplied images
- Image-generation or image-editing capability

## Output

By default, the skill returns only the finished poster.

Ask explicitly if you also want the selected style, creative direction, composition notes, or generation prompt.
