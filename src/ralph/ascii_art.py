#!/usr/bin/env python3
"""ASCII art module for displaying images in the terminal."""

import argparse
import os
from pathlib import Path

from PIL import Image
from rich.console import Console
from rich.text import Text

console = Console()


def get_ralph_image_path() -> Path:
    """Get the path to the bundled ralph.jpg image."""
    return Path(__file__).parent / "ralph.jpg"


def display_ralph_mascot(max_height: int = 20, dark_mode: bool = True) -> None:
    """Display the Ralph mascot ASCII art.

    Args:
        max_height: Maximum height in terminal lines (default 20 for compact display)
        dark_mode: Use dark mode colors (default True, assumes dark terminal)
    """
    image_path = get_ralph_image_path()
    if image_path.exists():
        display_ascii_image(
            image_path=str(image_path),
            max_height=max_height,
            dark_mode=dark_mode,
            contrast_factor=1.5,
        )


DEFAULT_ASPECT_RATIO = 0.43

# ASCII characters for different display modes
# Characters ordered from darkest to lightest for light mode (dark text on light background)
LIGHT_MODE_CHARS = (
    "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/|()1{}[]?-_+~<>i!lI;:,\"^`'. "
)
# Characters ordered from lightest to darkest for dark mode (light text on dark background)
DARK_MODE_CHARS = LIGHT_MODE_CHARS[::-1]
# Default to light mode
ASCII_CHARS = LIGHT_MODE_CHARS


# Function to adjust contrast of an image
def adjust_contrast(image, factor=1.5):
    """
    Adjust the contrast of an image.

    Args:
        image: PIL Image object
        factor: Contrast adjustment factor. Higher values increase contrast.
               1.0 means no change, values < 1.0 decrease contrast.

    Returns:
        PIL Image with adjusted contrast
    """
    # Convert to grayscale if not already
    if image.mode != "L":
        image = grayify(image)

    # Get the minimum and maximum pixel values
    pixels = list(image.getdata())
    min_val = min(pixels)
    max_val = max(pixels)

    # Calculate contrast adjustment factors
    range_val = max_val - min_val
    if range_val == 0:  # Avoid division by zero
        return image

    # Create a new image with adjusted contrast
    result = Image.new("L", image.size)
    width, height = image.size

    for y in range(height):
        for x in range(width):
            pixel = image.getpixel((x, y))

            # Normalize the pixel value to [0, 1]
            normalized = (pixel - min_val) / range_val

            # Apply contrast adjustment
            adjusted = ((normalized - 0.5) * factor + 0.5) * 255

            # Clamp to valid range
            adjusted = max(0, min(255, int(adjusted)))

            result.putpixel((x, y), adjusted)

    return result


# Function to map pixels to ASCII
def pixel_to_ascii(image):
    """
    Convert a grayscale image to ASCII characters.

    Args:
        image: A grayscale (mode 'L') PIL image

    Returns:
        A string of ASCII characters representing the image
    """
    # Ensure we have a grayscale image
    if image.mode != "L":
        image = image.convert("L")

    # Get pixel data
    pixels = list(image.getdata())

    # Find min and max for better mapping
    min_val = min(pixels)
    max_val = max(pixels)
    val_range = max_val - min_val

    # If all pixels are the same, avoid division by zero
    if val_range == 0:
        val_range = 1

    # Map pixels to ASCII characters with improved scaling
    ascii_str = ""
    for pixel in pixels:
        # Normalize pixel value to [0, 1] based on the image's actual range
        normalized = (pixel - min_val) / val_range

        # Map to ASCII character index
        char_idx = min(int(normalized * (len(ASCII_CHARS) - 1)), len(ASCII_CHARS) - 1)
        ascii_str += ASCII_CHARS[char_idx]

    return ascii_str


# Function to resize image maintaining aspect ratio, adjusted for terminal width and height
def resize_image(image, max_width, max_height, char_aspect_ratio):
    aspect_ratio = image.width / image.height
    new_width = max_width
    new_height = int(max_width / aspect_ratio * char_aspect_ratio)

    if new_height > max_height:
        new_height = max_height
        new_width = int(max_height * aspect_ratio / char_aspect_ratio)

    resized_image = image.resize((new_width, new_height))
    return resized_image


# Function to convert image to grayscale using luma weighted sum (Y706)
def grayify(image):
    # Use the recommended luma formula: Y706 = 0.2126*R + 0.7152*G + 0.0722*B
    # This preserves better luminance perception compared to simple grayscale conversion

    # If already grayscale, just return the image
    if image.mode == "L":
        return image

    width, height = image.size
    result = Image.new("L", (width, height))

    # Process each pixel
    for x in range(width):
        for y in range(height):
            # Get RGB values
            r, g, b = image.getpixel((x, y))[
                :3
            ]  # Ensure we get only RGB if there's alpha

            # Apply luma weighted sum formula
            luma = int(0.2126 * r + 0.7152 * g + 0.0722 * b)

            # Set the grayscale pixel
            result.putpixel((x, y), luma)

    return result


# Function to create an image with a circle for aspect ratio calibration
def create_circle_ascii_image(max_width, max_height, char_aspect_ratio):
    circle_ascii = []
    height_aspect_ratio_adjusted = int(max_height / char_aspect_ratio)
    radius = min(max_width // 2, height_aspect_ratio_adjusted // 2)
    center_x, center_y = max_width // 2, max_height // 2

    for y in range(max_height):
        line = ""
        for x in range(max_width):
            distance = (
                ((x - center_x) ** 2) + ((y - center_y) ** 2) / (char_aspect_ratio**2)
            ) ** 0.5
            if distance < radius:
                line += "@"
            else:
                line += " "
        circle_ascii.append(line)
    return "\n".join(circle_ascii)


# Convert image to ASCII art and display using Rich with full color
def display_ascii_image(
    image_path=None,
    max_width=None,
    max_height=None,
    char_aspect_ratio=DEFAULT_ASPECT_RATIO,
    circle=False,
    dark_mode=False,
    contrast_factor=1.5,
):
    try:
        # Get terminal size for dynamic resizing
        try:
            terminal_size = os.get_terminal_size()
            terminal_width = max_width if max_width else terminal_size.columns
            terminal_height = max_height if max_height else terminal_size.lines - 1
        except (OSError, AttributeError):
            # Fallback if terminal size can't be determined
            terminal_width = max_width if max_width else 80
            terminal_height = max_height if max_height else 24

        # Set the appropriate character set based on dark mode preference
        global ASCII_CHARS
        ASCII_CHARS = DARK_MODE_CHARS if dark_mode else LIGHT_MODE_CHARS

        if not (circle or image_path):
            console.print(
                "[red]Error: Must specify an image path or circle flag.[/red]"
            )
            return
        elif circle and image_path:
            console.print(
                "[red]Error: Cannot specify both image path and circle flag.[/red]"
            )
            return

        if circle:
            # Create a calibration circle ASCII art
            ascii_img = create_circle_ascii_image(
                terminal_width, terminal_height, char_aspect_ratio
            )

            for line in ascii_img.splitlines():
                colored_line = Text()
                # Adjust color based on dark mode
                if dark_mode:
                    for char in line:
                        colored_line.append(
                            char, style="white" if char == " " else "black"
                        )
                else:
                    for char in line:
                        colored_line.append(
                            char, style="white" if char == "@" else "black"
                        )
                console.print(colored_line)
        else:
            # Open and process the image
            image = Image.open(image_path)
            image = resize_image(
                image, terminal_width, terminal_height, char_aspect_ratio
            )

            # Convert image pixels to ASCII characters with the specified contrast factor
            # First apply grayscale using luma
            gray_image = grayify(image)
            # Then apply contrast adjustment
            contrast_image = adjust_contrast(gray_image, contrast_factor)
            # Convert to ASCII using the contrast-adjusted image
            ascii_str = pixel_to_ascii(contrast_image)

            # Split the ASCII string into rows
            img_width = image.width
            ascii_img = "\n".join(
                [
                    ascii_str[i : i + img_width]
                    for i in range(0, len(ascii_str), img_width)
                ]
            )

            # Display using Rich with full color
            for y, line in enumerate(ascii_img.splitlines()):
                colored_line = Text()
                for x, char in enumerate(line):
                    # Make sure we're within image bounds
                    if x < image.width and y < image.height:
                        # Get the original color from the image
                        pixel = image.getpixel((x, y))

                        # Handle different image modes
                        if image.mode == "RGB":
                            r, g, b = pixel
                        elif image.mode == "RGBA":
                            r, g, b, a = pixel
                        elif image.mode == "L":
                            r = g = b = pixel
                        else:
                            # For other modes, convert to RGB
                            rgb_image = image.convert("RGB")
                            r, g, b = rgb_image.getpixel((x, y))

                        # Create RGB color string
                        color = f"rgb({r},{g},{b})"

                        # Apply appropriate character for the brightness
                        colored_line.append(char, style=color)
                    else:
                        # If outside image bounds, use a default character
                        colored_line.append(" ")
                console.print(colored_line)

    except FileNotFoundError:
        console.print(f"[red]Error: The file '{image_path}' was not found.[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


# Main function using argparse to handle CLI input
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert an image to ASCII art and display it in the terminal."
    )
    parser.add_argument(
        "image_path", type=str, nargs="?", default=None, help="Path to the image file."
    )
    parser.add_argument(
        "-w",
        "--max-width",
        type=int,
        default=None,
        help="Maximum width of the ASCII art in characters. Defaults to terminal width.",
    )
    parser.add_argument(
        "-t",
        "--max-height",
        type=int,
        default=None,
        help="Maximum height of the ASCII art in lines. Defaults to terminal height.",
    )
    parser.add_argument(
        "-a",
        "--char-aspect-ratio",
        type=float,
        default=DEFAULT_ASPECT_RATIO,
        help="Aspect ratio adjustment for characters.",
    )
    parser.add_argument(
        "-c",
        "--circle",
        action="store_true",
        help="Output a circle for aspect ratio calibration.",
        default=False,
    )
    parser.add_argument(
        "-d",
        "--dark-mode",
        action="store_true",
        help="Use dark mode ASCII characters (light text on dark background).",
        default=False,
    )
    parser.add_argument(
        "--contrast",
        type=float,
        default=1.5,
        help="Contrast adjustment factor. Higher values increase contrast. Default is 1.5",
    )

    args = parser.parse_args()
    if args.circle and args.image_path:
        console.print(
            "[red]Error: Cannot specify both image path and circle flag.[/red]"
        )
    else:
        display_ascii_image(
            args.image_path,
            args.max_width,
            args.max_height,
            args.char_aspect_ratio,
            args.circle,
            args.dark_mode,
            args.contrast,
        )
