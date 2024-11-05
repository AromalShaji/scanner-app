import twain
import os
import sys
from fpdf import FPDF
import time
import base64
from io import BytesIO
from PIL import Image

def list_scanners():
    """Lists available scanners."""
    try:
        sm = twain.SourceManager(0)
        scanners = sm.GetSourceList()
        for scanner in scanners:
            print(scanner)
    except Exception as e:
        print("An error occurred while listing scanners:")
        print(e)

def scan_document(scanner_name):
    """Scans a document using the specified scanner."""
    source = None
    sm = None

    try:
        print("Initializing Source Manager...")
        sm = twain.SourceManager(0)

        print(f"Opening source: {scanner_name}...")
        source = sm.OpenSource(scanner_name)

        if not source:
            print(f"Failed to open source: {scanner_name}")
            return

        # Set scanner capabilities
        print("Setting scanner resolution and pixel type...")
        source.SetCapability(twain.ICAP_XRESOLUTION, twain.TWTY_FIX32, 300)  # 300 DPI
        source.SetCapability(twain.ICAP_PIXELTYPE, twain.TWTY_UINT16, 2)  # Grayscale

        print("Requesting acquisition...")
        source.RequestAcquire(0, 0)

        # Adding a delay to allow the scanner to warm up
        time.sleep(5)

        print("Performing scan...")
        result = source.XferImageNatively()

        if result:
            print("Scan successful, processing image...")
            handle, info = result

            # Verify result type and content
            if not isinstance(handle, twain.ImageHandle) or not isinstance(info, tuple):
                raise ValueError("Unexpected image data format")

            # Convert the scanned image data to a format suitable for Base64 encoding
            image_data = twain.DIBToImage(handle)
            image = Image.frombytes('L', (info[0], info[1]), image_data)

            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # Output the Base64 encoded image data to Electron
            print(f"data:image/png;base64,{img_str}")
        else:
            print("Error: No image acquired")
            print("Error during scanning: No image acquired.")
    except twain.exceptions.SequenceError as e:
        print(f"Sequence Error: {e}")
    except twain.exceptions.TwainError as e:
        print(f"Twain Error: {e}")
    except ValueError as e:
        print(f"Value Error: {e}")
    except Exception as e:
        print(f"General Error: {e}")
    finally:
        # Clean up resources
        print("Entering cleanup...")
        if source:
            cleanup_source(source)
        cleanup_source_manager(sm)

def convert_image_to_pdf(image_path):
    """Converts the scanned image to a PDF."""
    pdf = FPDF()
    pdf.add_page()

    # Insert the scanned image into the PDF
    pdf.image(image_path, x=10, y=10, w=180)  # Adjust these dimensions as needed

    pdf_filename = "scanned_documentx1.pdf"
    pdf.output(pdf_filename)
    return pdf_filename

def cleanup_source(source):
    """Resets the scanner source and ensures cleanup."""
    try:
        if source:
            print("Attempting to stop source if it's still acquiring...")
            
            # Safely stop any ongoing acquisition
            if hasattr(source, 'stop'):
                print("Stopping acquisition...")
                try:
                    source.stop()
                    time.sleep(1)  # Ensure a slight delay after stop
                except Exception as e:
                    print(f"Error during Stop(): {e}")

            # Reset the source to ensure it's back to a neutral state
            if hasattr(source, 'reset'):
                print("Resetting source...")
                try:
                    source.reset()
                    time.sleep(1)  # Ensure reset is complete
                except Exception as e:
                    print(f"Error during Reset(): {e}")

            # Attempt to destroy the source to free it
            print("Attempting to destroy source...")
            if hasattr(source, 'destroy'):
                try:
                    source.destroy()
                except Exception as e:
                    print(f"Error during source destroy: {e}")
            else:
                print("Source object has no 'destroy' method.")
    except Exception as e:
        print(f"Error during source cleanup: {e}")
    finally:
        print("Source cleanup process completed.")

def cleanup_source_manager(sm):
    """Safely clean up the Source Manager."""
    if sm:
        try:
            print("Destroying Source Manager...")
            sm.destroy()
            print("Source Manager destroyed successfully.")
        except Exception as e:
            print(f"Failed to destroy Source Manager: {e}")

if __name__ == "__main__":
    if "--list-scanners" in sys.argv:
        list_scanners()
    elif "--scan" in sys.argv:
        scanner_name = sys.argv[sys.argv.index("--scan") + 1]
        scan_document(scanner_name)
    else:
        print("Invalid command.")