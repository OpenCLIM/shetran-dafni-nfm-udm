import subprocess
import shutil
from glob import glob
import os
import datetime
from zipfile import ZipFile, ZIP_DEFLATED


# TODO:
#  - The library file with a number is not needed, but the results are. The UDM exe creates the UDM library file and also a landcover with 11/12 changed to 1/2 (landcover...cal.asc)

# Create a function that writes log files:
def logger(file_path, text, write_mode='a'):
    with open(file_path, write_mode) as log:
        log.write(text + "\n")

# Get the path to the input dataset:
data_path = os.getenv('DATA_PATH', '/data')

# Set the input and output paths as subdirectories of the path above:
inputs = os.path.join(data_path, 'inputs')
outputs = os.path.join(data_path, 'outputs')

# Create a folder to hold the SHETRAN model software and simulation files:
run_path = os.path.join(outputs, 'run_folder')

# If there are existing outputs then remove these: # Uncomment these once UDM is working
if os.path.exists(outputs):
    shutil.rmtree(outputs)

# Create a new (empty) output folder:
os.mkdir(outputs)
os.mkdir(run_path)

# Set up a log file:
log_file = os.path.join(outputs, 'logfile.txt')
logger(log_file, 'LOG FILE', write_mode='w')

try:
    # Get a list of the inputs and crop them to the catchment of interest:
    catchment_name = os.getenv('CATCHMENT_NAME')
    catchment_files = [f for f in os.listdir(inputs) if catchment_name in f]

    logger(log_file, f'CATCHMENT: {catchment_name}')

    # --- Copy desired NFM inputs from the list:

    # Create a parameter for selecting the no/correct NFM:
    nfm_scenario = os.getenv('NFM_SCENARIO')

    # Get the names of the NFM files we're interested in:
    if nfm_scenario == 'max':
        nfm_files = [f for f in catchment_files if 'NFM_max' in f]
    elif nfm_scenario == 'balanced':
        nfm_files = [f for f in catchment_files if 'NFM_balanced' in f]
    else:
        nfm_files = []
    logger(log_file, f'NFM DATA: {nfm_files}')

    # Rename the NFM files to remove the max/balanced and move it into the catchment folder:
    for f in nfm_files:
        f_new = f.replace('max_', '').replace('balanced_', '')
        shutil.copy(inputs + '/' + f, run_path + '/' + f_new)

    # --- Copy desired UDM inputs from the list:

    # Create a parameter for selecting the no/correct UDM:
    udm_scenario = os.getenv('UDM_SCENARIO')

    # Set the names of the desired UDM files:
    if udm_scenario == 'Baseline':
        udm_file = f"{catchment_name}_LandCover_UDM_2017.asc"
    else:
        udm_file = f"{catchment_name}_LandCover_UDM_GB_LandCover_{udm_scenario}.asc"

    logger(log_file, f'UDM SCENARIO: {udm_scenario}')
    logger(log_file, f'CHECK - UDM file name: {inputs + "/" + udm_file}')
    logger(log_file, f'CHECK - UDM file exists: {os.path.exists(inputs+"/"+udm_file)}')
    logger(log_file, f'CHECK - run_folder exists: {os.path.exists(run_path)}')

    # Copy the UDM file into the run folder:
    try:
        shutil.copy(f'{inputs}/{udm_file}', f"{run_path}/{catchment_name}_LandCover_UDM.asc")
    except Exception as E:
        logger(log_file, E)

    # --- Crop the inputs to only include the climate data for the desired RCM:
    climate_scenario = os.getenv('CLIMATE_SCENARIO')
    with ZipFile(f'{inputs}/{catchment_name}_climate_files_{climate_scenario}.zip', 'r') as zip_ref:
        zip_ref.extractall(run_path)

    # Find the Autocalibration LibraryFile and results and copy that in:
    autocal_library = [f for f in catchment_files if '_autocal_Library' in f][0]
    logger(log_file, f'CHECK - autocalibration library file exists: {os.path.exists(f"{inputs}/{autocal_library}")}')
    shutil.copy(f"{inputs}/{autocal_library}",
                run_path + '/' + autocal_library.replace(f'{catchment_name}_autocal_', ''))
    shutil.copy(f"{inputs}/{catchment_name}_results.csv", run_path + '/results.csv')

    # Copy the desired non-parameter based contents of the inputs folder into the run folder:
    catchment_files = [f for f in catchment_files if '_NFM_' not in f]
    catchment_files = [f for f in catchment_files if '_UDM_' not in f]
    catchment_files = [f for f in catchment_files if '_climate_files_' not in f]
    catchment_files = [f for f in catchment_files if '_autocal_' not in f]
    catchment_files = [f for f in catchment_files if 'results' not in f]
    for f in catchment_files:
        shutil.copy(inputs + '/' + f, run_path + '/' + f)
    logger(log_file, f'STATUS - Copied files to run folder.')

    # Run the UDM converter exe if required:
    # !! This is where the script breaks - it finds the setup file, but does not run through it - perhaps issue with library name?
    # I wonder whether we have an issue with libraries as we get a library error at the end if I make all of the required files by hand.
    # Google says that the error may be related to : Binding all of /usr from the host in to the container will replace all the basic libraries in the container with the versions from the host. Unless the host is an identical linux distro / version and has all the libraries the container needs under /usr then this will cause major problems. The programs in the container are expecting the container versions of basic libraries under /usr, not what you are supplying from the host.
    # UDM_input = UDM_input.replace('/', '\\')

    # print('CONTENTS: ' + run_path)
    # print(os.listdir(run_path))

    UDM_input = run_path + '/' + catchment_name
    logger(log_file, f'STATUS - running UDM using: ./shetran-setup-CEH2Types-linux {UDM_input}')
    if int(catchment_name) >= 200000:
        subprocess.call(['./shetran-setup-CEH2Types-linux', UDM_input])
    else:
        subprocess.call(['./shetran-setup-UDM-linux', UDM_input])
    # [This creates a new library file, which will need to be used in the next step: 2002_LibraryFile_UDM.xml]

    # Find the required library file:
    try:
        library = glob(os.path.join(run_path, '*_LibraryFile_UDM.xml'))[0]
    except IndexError:
        raise Exception('*_LibraryFile_UDM.xml file missing')
        logger(log_file, f'EXCEPTION - *_LibraryFile_UDM.xml file missing')

    # Run the SHETRAN prepare script:
    # [Use the prep...50.exe version]
    logger(log_file, f'STATUS - Preparing {library}')
    subprocess.call(['./shetran-prepare-snow', library])

    # Run the SHETRAN simulation:
    logger(log_file, "STATUS - running SHETRAN simulation")
    logger(log_file, glob(os.path.join(run_path, 'rundata_*')))
    subprocess.call(['./shetran-linux', '-f', glob(os.path.join(run_path, 'rundata_*'))[0]])

    # Get the title from the workflow parameter, or set a default:
    title = os.getenv('TITLE', 'SHETRAN output')
    description = ' '
    geojson = {}

    # Create the metadata:
    metadata = f"""{{
      "@context": ["metadata-v1"],
      "@type": "dcat:Dataset",
      "dct:language": "en",
      "dct:title": "{title}",
      "dct:description": "{description}",
      "dcat:keyword": [
        "shetran"
      ],
      "dct:subject": "Environment",
      "dct:license": {{
        "@type": "LicenseDocument",
        "@id": "https://creativecommons.org/licences/by/4.0/",
        "rdfs:label": null
      }},
      "dct:creator": [{{"@type": "foaf:Organization"}}],
      "dcat:contactPoint": {{
        "@type": "vcard:Organization",
        "vcard:fn": "DAFNI",
        "vcard:hasEmail": "support@dafni.ac.uk"
      }},
      "dct:created": "{datetime.datetime.now().isoformat()}Z",
      "dct:PeriodOfTime": {{
        "type": "dct:PeriodOfTime",
        "time:hasBeginning": null,
        "time:hasEnd": null
      }},
      "dafni_version_note": "created",
      "dct:spatial": {{
        "@type": "dct:Location",
        "rdfs:label": null
      }},
      "geojson": {geojson}
    }}
    """

    # Write the metadata:
    with open(os.path.join(outputs, 'metadata.json'), 'w') as f:
        f.write(metadata)


except Exception as E:
    logger(log_file, 'FAIL')
    logger(log_file, E)
