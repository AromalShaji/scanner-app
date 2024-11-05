import twain

def list_scanners():
    try:
        # Initialize TWAIN source manager
        sm = twain.SourceManager(0)
        
        # List available sources
        sources = sm.GetSourceList()
        
        if not sources:
            print("No scanners connected.")
            return
        
        connected_scanners = []
        
        for source_name in sources:
            source = None
            try:
                # Attempt to open the source
                source = sm.OpenSource(source_name)
                if source:
                    # If source is successfully opened, add it to the list
                    connected_scanners.append(source_name)
            except Exception as e:
                print(f"Error with source '{source_name}': {e}")
            finally:
                # Ensure source is properly managed
                if source:
                    try:
                        # Check if CloseSource is available
                        if hasattr(source, 'CloseSource'):
                            source.CloseSource()
                        else:
                            print(f"Source '{source_name}' does not support CloseSource.")
                    except Exception as e:
                        print(f"Error closing source '{source_name}': {e}")
        
        if connected_scanners:
            print(f"Connected scanners: {', '.join(connected_scanners)}")
        else:
            print("No scanners connected.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    list_scanners()
