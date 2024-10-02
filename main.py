from openai import OpenAI
from tools.api_key_check import load_api_key
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps
import numpy as np
import cv2
import requests
import io

api_key = load_api_key("tools/api_key.txt")

client = OpenAI(api_key=api_key)


def display_image(img):
    """Display an image directly on the canvas."""
    global img_tk, canvas

    # Resize the image to fit the display area (e.g., 400x400)
    img.thumbnail((400, 400), Image.Resampling.LANCZOS)  # Updated resampling method
    img_tk = ImageTk.PhotoImage(img)

    # Clear the canvas and create a new image
    canvas.delete("all")  # Clear existing drawings
    canvas.create_image(200, 200, image=img_tk, anchor=tk.CENTER)  # Place image at the center


def pre_existing_image(image_url, prompt):
    """Work on a pre-existing image."""
    response = client.images.edit(
        model="dall-e-2",
        image=image_url,
        prompt=prompt,
    )
    edited_image_url = response.data.url
    print("Edited Image URL:", edited_image_url)

def new_image(prompt):
    global img  # Make sure to declare img as global
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    print("Generated Image URL:", image_url)

    # Fetch and display the generated image
    response = requests.get(image_url)
    image_data = response.content
    img = Image.open(io.BytesIO(image_data))  # Update the global img variable
    initialize_mask()  # Reinitialize the mask to match the new image
    display_image(img)  # Display the image




# Global variables to hold images, masks, and states for undo
img = None
img_tk = None
mask_prompt = ""
# At the beginning of your script, define the global variable
image_description = ""
canvas = None
mask = None
drawing = False
mask_states = []  # Stack to hold mask states for undo functionality


def setup_gui():
    global root, canvas, upload_btn, save_btn, width_scale

    root = tk.Tk()
    root.title("Image Upload and Mask Tool")

    upload_btn = tk.Button(root, text="Upload PNG Image", command=upload_image)
    upload_btn.pack(pady=10)

    canvas = tk.Canvas(root, bg='white', cursor="cross", width=400, height=400)
    canvas.pack(pady=10, side="top")  # Ensure it's visibly on top
    canvas.bind("<Button-1>", start_drawing) 
    canvas.bind("<B1-Motion>", draw)  # Continue drawing on drag
    canvas.bind("<ButtonRelease-1>", stop_drawing)  # Stop drawing on release


    save_btn = tk.Button(root, text="Save Masked Image", command=save_image)
    save_btn.pack(pady=10)

    # Setup other components...
    save_generated_btn = tk.Button(root, text="Save Generated Image", command=save_generated_image)
    save_generated_btn.pack(pady=10)

    width_scale = tk.Scale(root, from_=1, to=10, orient='horizontal', label='Mask Width', command=update_canvas)
    width_scale.set(3)
    width_scale.pack(pady=10)

    new_image_btn = tk.Button(root, text="Create a New Image", command=create_new_image)
    new_image_btn.pack(pady=5)

    variants_image_btn = tk.Button(root, text="Create Variants of an Image", command=create_variants_of_image)
    variants_image_btn.pack(pady=5)

    root.mainloop()

def test_event(event):
    print("Mouse position:", event.x, event.y)

def upload_image():
    """Open a file dialog to upload and display an image, resizing it."""
    global img, canvas, mask

    file_path = filedialog.askopenfilename(
        title="Select an Image File",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
    )

    if file_path:
        img = Image.open(file_path).convert('RGB')
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        initialize_mask()  # Initialize mask after resizing
        display_image(img)





def save_image():
    """Save the edited image with the applied mask, maintaining transparency."""
    global img, mask

    if img is None or mask is None:
        messagebox.showwarning("Warning", "No image or mask available to save.")
        return

    # Ensure the mask is in 'L' mode, then invert it
    if mask.mode != 'L':
        mask = mask.convert('L')
    inverted_mask = ImageOps.invert(mask)  # Invert the mask

    # Convert the PIL image to a NumPy array and add an alpha channel
    img_array = np.array(img.convert("RGBA"))  # Ensure the image is in RGBA format
    mask_array = np.array(inverted_mask)

    # Apply the inverted mask to the alpha channel: 0 where the mask is white (drawn areas), 255 elsewhere
    img_array[:, :, 3] = mask_array  # Update alpha channel with the inverted mask

    # Convert back to PIL image to save
    masked_img = Image.fromarray(img_array)

    # Open the save dialog with PNG as the only option
    output_path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG files", "*.png")],
        title="Save Masked Image"
    )

    if output_path:
        try:
            masked_img.save(output_path, format="PNG")  # Save specifically as PNG
            messagebox.showinfo("Success", f"Image saved to '{output_path}'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {e}")


def save_generated_image():
    """Save the currently displayed generated image to a file."""
    global img

    if img is None:
        messagebox.showwarning("Warning", "No generated image available to save.")
        return

    # Open a dialog for the user to choose where to save the image
    output_path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
        title="Save Generated Image"
    )

    if not output_path:
        return  # User cancelled the save

    # Try to save the image
    try:
        img_format = 'PNG' if output_path.endswith('.png') else 'JPEG'
        img.save(output_path, format=img_format)
        messagebox.showinfo("Success", f"Image successfully saved to '{output_path}'.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save the image: {e}")



def submit_text():
    """Retrieve the text from the entry widget and store it for later use."""
    global image_description, text_entry_window, entry_text

    # Retrieve text from entry widget
    image_description = entry_text.get()
    new_image(image_description)
    print("Saved image description:", image_description)  # You can remove this print later

    # Close the text entry window after submission
    text_entry_window.destroy()


def submit_mask_text():
    """Retrieve the text from the entry widget and store it for later use, then process images."""
    global image_description, text_entry_window, entry_text, file_path1, file_path2

    # Retrieve text from entry widget
    image_description = entry_text.get()
    print("Saved image description:", image_description)

    # Close the text entry window after submission
    text_entry_window.destroy()

    # Proceed to call the DALL-E API with the provided images and the prompt
    process_images_with_dalle(file_path1, file_path2, image_description)

def process_images_with_dalle(file_path1, file_path2, prompt):
    """Calls the DALL-E API to edit images based on the provided prompt."""
    try:
        # Load and resize images to 1024x1024
        with Image.open(file_path1) as img1, Image.open(file_path2) as img2:
            img1_resized = img1.resize((1024, 1024), Image.LANCZOS)
            img2_resized = img2.resize((1024, 1024), Image.LANCZOS)

            # Convert images to byte arrays for API submission
            img1_buffer = io.BytesIO()
            img1_resized.save(img1_buffer, format="PNG")
            img1_data = img1_buffer.getvalue()

            img2_buffer = io.BytesIO()
            img2_resized.save(img2_buffer, format="PNG")
            img2_data = img2_buffer.getvalue()

            # Proceed with API call (example API call below might need adjustments)
            response = client.images.edit(
                model="dall-e-2",
                image=img1_data,
                mask=img2_data,
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            image_url = response.data[0].url
            response = requests.get(image_url)
            image_data = response.content
            img = Image.open(io.BytesIO(image_data))
            display_image(img)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create image variant: {e}")

def create_new_image():
    """Function to handle creation of a new image with text input."""
    global entry_text, text_entry_window

    # Create a new top-level window for text input
    text_entry_window = tk.Toplevel(root)
    text_entry_window.title("Enter Image Description")

    # Add a label to guide the user
    label = tk.Label(text_entry_window, text="Enter a description for the new image:")
    label.pack(pady=(10, 0))

    # Add a text entry widget
    entry_text = tk.Entry(text_entry_window, width=50)
    entry_text.pack(pady=10, padx=10)

    # Add a submit button
    submit_button = tk.Button(text_entry_window, text="Submit", command=submit_text)
    submit_button.pack(pady=(0, 10))


def update_canvas(val):
    """Trigger a canvas update whenever the mask width is adjusted."""
    global mask, mask_states, canvas, img_tk, img

    canvas.delete("all")  # Clear the canvas

    if img is not None:
        img_tk = ImageTk.PhotoImage(img)  # Reconvert the image for Tkinter
        canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)  # Redraw the image


def start_drawing(event):
    """Start drawing on the mask."""
    global drawing
    drawing = True
    print("Started drawing")  # Debug: Check if function is called
    draw(event)

def stop_drawing(event):
    """Stop drawing on the mask."""
    global drawing
    drawing = False
    print("Stopped drawing")  # Debug: Check if function is called

def draw(event):
    global mask, drawing
    if drawing and mask is not None:
        draw = ImageDraw.Draw(mask)
        x, y = event.x, event.y
        r = width_scale.get() + 10
        draw.ellipse((x-r, y-r, x+r, y+r), fill=255)  # Fill with 255 (fully opaque in 'L' mode)
        display_image_with_mask()



def display_image_with_mask():
    global img, mask, canvas, img_tk

    if img is not None and mask is not None:
        print("Image size:", img.size)  # Debug sizes
        print("Mask size:", mask.size)  # Debug sizes

        # Ensure img is in RGB
        img_rgb = img.convert("RGB")

        # Create a red overlay image of the same size
        red_overlay = Image.new('RGB', img.size, 'red')

        # Ensure mask is in the correct mode and used as the mask
        mask_l = mask.convert("L")
        print("Mask mode after conversion:", mask_l.mode)  # Debug mode

        # Composite the images using the mask
        masked_img = Image.composite(red_overlay, img_rgb, mask_l)

        # Convert the result for display
        img_tk = ImageTk.PhotoImage(masked_img)
        canvas.create_image(200, 200, image=img_tk, anchor=tk.CENTER)





def initialize_mask():
    """Initialize a transparent mask the same size as the image."""
    global mask
    if img is not None:
        mask = Image.new('L', img.size, 0)  # Create a grayscale image with 0 (transparent)
        print("Mask initialized for new image size:", img.size)




def apply_mask_to_image():
    """Apply the non-masked area as transparent."""
    global img, mask
    if img is not None and mask is not None:
        # Create an RGBA version of the image if not already
        img_rgba = img.convert("RGBA")
        # Apply mask: Set alpha to 0 where mask is painted (cut out)
        img_array = np.array(img_rgba)
        mask_array = np.array(mask)
        img_array[mask_array > 0, 3] = 0  # Set alpha to 0 where mask > 0
        # Update img to the new image with the mask applied
        img = Image.fromarray(img_array)


    


def create_variants_of_image():
    global root, entry_text, text_entry_window, image_description, file_path1, file_path2

    # Ask user to select the first image
    file_path1 = filedialog.askopenfilename(
        title="Select the first image",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
    )
    if not file_path1:
        messagebox.showinfo("Cancelled", "First image selection cancelled.")
        return

    # Ask user to select the second image
    file_path2 = filedialog.askopenfilename(
        title="Select the second image",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
    )
    if not file_path2:
        messagebox.showinfo("Cancelled", "Second image selection cancelled.")
        return

    # Create a new top-level window for text input
    text_entry_window = tk.Toplevel(root)
    text_entry_window.title("Enter Image Description")

    # Add a label to guide the user
    label = tk.Label(text_entry_window, text="Enter a description for the new image:")
    label.pack(pady=(10, 0))

    # Add a text entry widget
    entry_text = tk.Entry(text_entry_window, width=50)
    entry_text.pack(pady=10, padx=10)

    # Add a submit button
    submit_button = tk.Button(text_entry_window, text="Submit", command=submit_mask_text)
    submit_button.pack(pady=(0, 10))


setup_gui()