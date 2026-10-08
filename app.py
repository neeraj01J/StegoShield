from flask import Flask, render_template, request, send_file
from PIL import Image, UnidentifiedImageError
import io

app = Flask(__name__)

# Render Free has limited RAM.
# Reject extremely large uploaded files before processing.
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12 MB

END_MARKER = "###END###"

# Maximum image dimension used for processing.
# Large phone photos will be resized while keeping their aspect ratio.
MAX_DIMENSION = 2000


def prepare_image(image):
    """
    Convert the image to RGB and reduce very large images
    to keep memory usage low.
    """

    image = image.convert("RGB")

    width, height = image.size

    largest_dimension = max(width, height)

    if largest_dimension > MAX_DIMENSION:
        scale = MAX_DIMENSION / largest_dimension

        new_width = int(width * scale)
        new_height = int(height * scale)

        image = image.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

    return image


def hide_message(image, message):

    image = prepare_image(image)

    message = message + END_MARKER

    message_bytes = message.encode("utf-8")

    # Compact RGB pixel data
    pixel_data = bytearray(image.tobytes())

    required_bits = len(message_bytes) * 8

    if required_bits > len(pixel_data):
        raise ValueError(
            "Message is too long for this image. "
            "Please use a larger image or a shorter message."
        )

    bit_index = 0

    for byte in message_bytes:

        for bit in range(7, -1, -1):

            message_bit = (byte >> bit) & 1

            pixel_data[bit_index] = (
                pixel_data[bit_index] & 0xFE
            ) | message_bit

            bit_index += 1

    encoded_image = Image.frombytes(
        "RGB",
        image.size,
        bytes(pixel_data)
    )

    output = io.BytesIO()

    encoded_image.save(
        output,
        format="PNG",
        optimize=True
    )

    output.seek(0)

    return output


def extract_message(image):

    image = prepare_image(image)

    pixel_data = image.tobytes()

    marker = END_MARKER.encode("utf-8")

    message_bytes = bytearray()

    current_byte = 0
    bit_count = 0

    for value in pixel_data:

        current_byte = (
            current_byte << 1
        ) | (value & 1)

        bit_count += 1

        if bit_count == 8:

            message_bytes.append(current_byte)

            if message_bytes.endswith(marker):

                result = message_bytes[
                    :-len(marker)
                ]

                return result.decode(
                    "utf-8",
                    errors="replace"
                )

            current_byte = 0
            bit_count = 0

    return "No hidden message found."


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/hide", methods=["POST"])
def hide():

    try:

        if "image" not in request.files:
            return "No image uploaded.", 400

        image_file = request.files["image"]

        if not image_file.filename:
            return "No image selected.", 400

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not message:
            return "Message cannot be empty.", 400

        # Open image
        image = Image.open(image_file)

        # Verify that the image can actually be decoded
        image.verify()

        # Re-open after verify()
        image_file.seek(0)

        image = Image.open(image_file)

        output = hide_message(
            image,
            message
        )

        return send_file(
            output,
            mimetype="image/png",
            as_attachment=True,
            download_name="steganography_image.png"
        )

    except Image.DecompressionBombError:

        return (
            "Image contains too many pixels. "
            "Please use a smaller image.",
            400
        )

    except UnidentifiedImageError:

        return (
            "The uploaded file is not a valid image.",
            400
        )

    except ValueError as e:

        return str(e), 400

    except Exception as e:

        print("HIDE ERROR:", repr(e))

        return (
            "Unable to process the image.",
            400
        )


@app.route("/extract", methods=["POST"])
def extract():

    try:

        if "image" not in request.files:
            return "No image uploaded.", 400

        image_file = request.files["image"]

        if not image_file.filename:
            return "No image selected.", 400

        image = Image.open(image_file)

        message = extract_message(image)

        return message

    except Image.DecompressionBombError:

        return (
            "Image contains too many pixels. "
            "Please use a smaller image.",
            400
        )

    except UnidentifiedImageError:

        return (
            "The uploaded file is not a valid image.",
            400
        )

    except Exception as e:

        print("EXTRACT ERROR:", repr(e))

        return (
            "Unable to extract the message.",
            400
        )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )