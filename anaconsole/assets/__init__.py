import importlib.resources
import io


def load_file_stream(file_name: str, package: str = 'anaconsole.assets') -> io.BytesIO:
    """
    Loads a font file from a package and returns a BytesIO stream suitable for pygame.font.Font.

    :param file_name: The name of the file (e.g., "my_font.ttf").
    :param package: The dotted path to the package containing the file.
    :return: BytesIO object containing the font data.
    """
    with importlib.resources.open_binary(package, file_name) as font_file:
        return io.BytesIO(font_file.read())
