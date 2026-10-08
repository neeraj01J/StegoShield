from flask import Flask, render_template, request, send_file
from PIL import Image
import io

app = Flask(__name__)


def hide_message(image, message):
    image = image.convert("RGB")

    # End marker
    message = message + "###END###"
    binary_message = ''.join(format(ord(char), '08b') for char in message)

    pixels = list(image.getdata())

    if len(binary_message) > len(pixels) * 3:
        raise ValueError("Message is too long for this image.")

    new_pixels = []
    bit_index = 0

    for pixel in pixels:
        r, g, b = pixel
        rgb = [r, g, b]

        for i in range(3):
            if bit_index < len(binary_message):
                rgb[i] = (rgb[i] & 254) | int(binary_message[bit_index])
                bit_index += 1

        new_pixels.append(tuple(rgb))

    image.putdata(new_pixels)

    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return output


def extract_message(image):
    image = image.convert("RGB")

    binary = ""

    for pixel in image.getdata():
        for value in pixel:
            binary += str(value & 1)

    message = ""

    for i in range(0, len(binary), 8):
        byte = binary[i:i + 8]

        if len(byte) < 8:
            break

        char = chr(int(byte, 2))
        message += char

        if message.endswith("###END###"):
            return message[:-9]

    return "No hidden message found."


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/hide", methods=["POST"])
def hide():
    try:
        image_file = request.files["image"]
        message = request.form["message"]

        image = Image.open(image_file)

        output = hide_message(image, message)

        return send_file(
            output,
            mimetype="image/png",
            as_attachment=True,
            download_name="steganography_image.png"
        )

    except Exception as e:
        return f"Error: {str(e)}", 400


@app.route("/extract", methods=["POST"])
def extract():
    try:
        image_file = request.files["image"]

        image = Image.open(image_file)

        message = extract_message(image)

        return message

    except Exception as e:
        return f"Error: {str(e)}", 400


if __name__ == "__main__":
    app.run(debug=True)