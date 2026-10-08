from flask import Flask, render_template, request, send_file
from PIL import Image
import io

app = Flask(__name__)

# Prevent extremely large uploads from consuming all server memory.
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB


END_MARKER = "###END###"


def hide_message(image, message):
    # Convert image to RGB
    image = image.convert("RGB")

    # Add end marker
    message = message + END_MARKER

    # Convert message directly to bytes
    message_bytes = message.encode("utf-8")

    # Convert image pixels into a compact mutable byte array.
    # RGB image = 3 bytes per pixel.
    pixel_data = bytearray(image.tobytes())

    # Each byte stores one message bit.
    required_bits = len(message_bytes) * 8

    if required_bits > len(pixel_data):
        raise ValueError(
            "Message is too long for this image."
        )

    bit_index = 0

    for byte in message_bytes:
        for bit in range(7, -1, -1):
            message_bit = (byte >> bit) & 1

            # Clear the least significant bit and insert message bit
            pixel_data[bit_index] = (
                pixel_data[bit_index] & 0xFE
            ) | message_bit

            bit_index += 1

    # Create the modified image
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
    image = image.convert("RGB")

    pixel_data = image.tobytes()

    message_bytes = bytearray()

    current_byte = 0
    bit_count = 0

    for value in pixel_data:

        # Read LSB
        current_byte = (
            current_byte << 1
        ) | (value & 1)

        bit_count += 1

        if bit_count == 8:

            message_bytes.append(current_byte)

            # Check for end marker without creating
            # a huge binary string.
            if message_bytes.endswith(
                END_MARKER.encode("utf-8")
            ):
                result = message_bytes[
                    :-len(END_MARKER)
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

        message = request.form.get("message", "").strip()

        if not message:
            return "Message cannot be empty.", 400

        # Open uploaded image
        image = Image.open(image_file)

        # Process image
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

    except Exception as e:
        print("HIDE ERROR:", repr(e))
        return f"Error: {str(e)}", 400


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

    except Exception as e:
        print("EXTRACT ERROR:", repr(e))
        return f"Error: {str(e)}", 400


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )