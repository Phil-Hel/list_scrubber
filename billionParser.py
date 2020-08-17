#!/bin/python3
import argparse
import os
import re
import magic
from tqdm.auto import tqdm
import tempfile
import concurrent.futures
import datetime

parser = argparse.ArgumentParser(description='Find all lines\
     in doc-structure with a certain pattern.')
NO_LOCATION = "<NO_LOCATION>"
BLACKLIST_FILE_TYPES = ["application/x-sqlite3", "text/x-python", "application/vnd.debian.binary-package",\
     'text/x-objective-c', "application/octet-stream", "application/zlib", 'application/x-dosexec', \
         'text/x-fortran', 'image/x-portable-pixmap']
fileSourcePath = os.path.join(*'Documents,UserPasswordLists,data, '.split(","))
fileTargetPath = os.path.join(*'directoryToSaveTo,whereverYouWant,nameYourFile.txt'.split(","))


start = datetime.datetime.now()

def findFiles(location, ignore):
    tqdm.write("Loading Files... ")
    files = []
    types = set()
    numberDirs = 0
    for r, d, f, in os.walk(location):
        for file in f:
            if not BLACKLIST_FILE_TYPES.__contains__(magic.from_file(os.path.join(r, file), mime=True)) and ignore != os.path.join(r, file):
                types.add(magic.from_file(os.path.join(r, file), mime=True))
                files.append(os.path.join(r, file))
    return files, types


def searchingThroughFiles(location, pattern, verbose, separate, lastname, firstname, output="./"):
    """
    This function is looking through all the files to find matches and handles where to write them to.
    """
    try:
        if (lastname and firstname): 
            pattern = f"({firstname}[.]*{lastname}[.]*@|[.]*{lastname}[.]*{firstname}[.]*@)"
            tqdm.write(f'Name pattern ([.]*{firstname}[.]*{lastname}[.]*@|[.]*{lastname}[.]*{firstname}[.]*@) initiated.')
        if output:
            filesTo = createTargetFiles(output)
            with tempfile.TemporaryDirectory() as tempDirect:
                tqdm.write(f"Created temporary dir at {tempDirect}")
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    count_sum = 0
                    paths = []
                    t = tqdm(total=len(location), desc="Search pattern", leave=False, smoothing=0.001, unit="docs", position=0)
                    results = [executor.submit(thread_writing, file, pattern, tempDirect) for file in location]
                    for r in concurrent.futures.as_completed(results):
                        path, count_local = r.result()
                        paths.append(path)
                        # tqdm.write(f"this was done: {path} and we found {count_local} matches")
                        count_sum += count_local
                        t.update(1)
                    t.close()
                    tqdm.write("-" * 50)
                    tqdm.write(f"{count_sum} matches were found.")
                    tqdm.write("-" * 50)
                    writeToTargetFile(paths, tempDirect, filesTo, separate)
            return filesTo
        else:
            for file in location:
                with open(file, "r") as file:
                    for line in file:
                        if re.search(r'{}'.format(pattern), f"*{line}*"):
                            tqdm.write(line)
    except FileExistsError:
        tqdm.write("There is already a file with that name!\nABORTED")
    except FileNotFoundError:
        tqdm.write(f"The directory {output} does not exist!\nABORTED")
    except UnicodeDecodeError:
        tqdm.write("There is an issue with the encoding. You most likely have a file that is not latin-1 readable.")
        tqdm.write("Watch the different file types with the -t option and add files you want to suppress in the Blacklist.")
    except KeyboardInterrupt:
        tqdm.write("\nThe program has been rage-quit")
    except IndexError as err:
        tqdm.write(f"We have an {err}. If -l was used, check if the file has additional unnecessary linebreaks at the end of the file.")

def thread_writing(file, pattern, tempDirect):
    count = 0
    something = "-".join(splitall(file)).replace(".", "")
    with open(os.path.join(tempDirect, "-".join(splitall(file)).replace(".", "")), "a", encoding="latin-1") as currentFile:
        with open(file, "r", encoding="latin-1") as f:
            for line in f:
                if re.search(f'{pattern}', line):
                    currentFile.write(line)
                    count += 1
    return "-".join(splitall(file)).replace(".", ""), count

def writeToTargetFile(paths, tempDirect, filesTo, separate):
    sepDescription =  "Writing to files" if (separate) else "Writing to master-file"
    writeProgress = tqdm(total=len(paths), desc=sepDescription, unit="docs", position=0, leave=False)
    for path in paths:
        with open(filesTo[0], "a", encoding="latin-1") as masterFile:
            with open(filesTo[1], "a", encoding="latin-1") as userFile:
                with open(filesTo[2], "a", encoding="latin-1") as passwordFile:
                    with open(os.path.join(tempDirect, path), "r", encoding="latin-1") as finishedFile:
                        for line in finishedFile:
                            masterFile.write(line)
                            if (separate): separatorUserPassword(line, userFile, passwordFile, separate)
                        writeProgress.update(1)
    writeProgress.close()
    if not (separate): 
        os.remove(filesTo[1])
        os.remove(filesTo[2])


def separatorUserPassword(line, userFile, passwordFile, separator):
    # in case the password is empty or only one part after split
    temp = line.split(f"{separator}", 1)
    if len(temp) == 2:
        user, password = line.split(f"{separator}", 1)
    else:
        user = line.split(f"{separator}", 1)[0]
        password = "\n"
    userFile.write(user + "\n")
    passwordFile.write(password) # doesn't need a linebreak, copied from file



def createTargetFiles(output):
    filename = os.path.basename(output.split(".")[0])
    
    if not os.path.exists(os.path.join(os.path.dirname(output), filename)):
        os.mkdir(os.path.join(os.path.dirname(output), filename))
        tqdm.write(f"Dir {filename} created for results.")
    else:
        tqdm.write(f"Dir {filename} already exists.\nPROCEED")
    create = ["main", "users", "password"]
    fileNames = []
    for c in create:
        f = open(os.path.join(os.path.join(os.path.dirname(output), filename), f"{filename}-{c}.txt"), "x")
        f.close()
        fileNames.append(os.path.join(os.path.join(os.path.dirname(output), filename), f"{filename}-{c}.txt"))
    tqdm.write(f"these are the files written to: {fileNames}")
    return fileNames

def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def parsedNames(list, verbose):
    """Used to parse names from a document of names."""
    names = []
    if verbose: tqdm.write(f"Parsing names in file {os.path.basename(list)}")
    with open(list, "r", encoding="utf-8") as nameList:
        for line in nameList:
            names.append(line.rstrip())
    return names


class Person():
    def __init__(self, name, output):
        self.extractFirstAndLastName(name)
        self.extractOutputName(output)


    def extractFirstAndLastName(self, name):
        fixedName = name.split(" ")
        self.firstname = fixedName[0]
        self.lastname = fixedName[1]
    
    def extractOutputName(self, output):
        self.outputFile = os.path.join(os.path.dirname(output), self.firstname + self.lastname.capitalize() + ".txt")

    def __str__(self):
        return f"firstname: {self.firstname}; lastname: {self.lastname}; outputFile: {self.outputFile}"

def Main():
    parser = argparse.ArgumentParser(description='Looking through files and merging lines \
        of specific pattern', epilog= "Example: "+ \
    f"python3 {__file__} {fileSourcePath} \
        anyKindOfPattern -o {fileTargetPath}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', "--verbose", action="store_true")
    group.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-su", "--suppressed", help="Shows type of files that are in Blacklist and excluded of search.",\
         action="store_true")
    parser.add_argument("-t", "--fileTypes", help="Shows type of files that have been found.", action="store_true")
    together = parser.add_argument_group("Optional name tags. Together they will trigger pattern: ([.]*forname[.]*lastname[.]*@|[.]*lastname[.]*forname[.]*@)")
    together.add_argument("-n", "--name", help="Will trigger search for users with name.", type=str)
    together.add_argument("-f", "--firstname", help="Will trigger search for users with firstname.", type=str)
    parser.add_argument("-s", "--separate", help="Separates user and password with your specified separator. Also separates the data into multiple files with users, passwords and main.", type=str)
    parser.add_argument("-i", "--ignore", help="Can ignore a certain file and exclude it from action.", type=str)
    parser.add_argument("sourceDirectory", help="The directory to be searched through.", type=str, default=NO_LOCATION)
    parser.add_argument("pattern", help="Pattern to look for.", type=str)
    parser.add_argument("-o", "--output", \
        help="Output result to file in specified location.\
            If no location is specified it'll be saved to this directory under name foundMatch.txt",\
        type=str)
    parser.add_argument("-l", "--list", help="List of names to check. Specify with txt file location. Specify names in style: \"firstname'whitespace'lastname\\n\". Automatically handled as with -f and -n and mutually exclusive.",\
         type=str)

    args = parser.parse_args()

    if not (args.list and (args.name or args.firstname)):
        fileList, types = findFiles(args.sourceDirectory, args.ignore)
        if (args.verbose):
            tqdm.write(f"Here are all the locations:\n[")
            for file in fileList:
                tqdm.write(f"{file}")
            tqdm.write("]")
            tqdm.write(f"location: {args.sourceDirectory}")
            tqdm.write(f"{len(fileList)} files found.")
        elif (args.quiet):
            tqdm.write(f"{len(fileList)} files found.")
        else:
            tqdm.write(f"{len(fileList)} files found in {args.sourceDirectory}.")
        if (args.suppressed):
            tqdm.write(f"These file types are ignored: {BLACKLIST_FILE_TYPES}")
        if (args.fileTypes):
            tqdm.write(f"These file types have been found: {types}")
        if (args.list):
            nameList = parsedNames(args.list, args.verbose)
            people = []
            for name in nameList:
                people.append(Person(name, args.output))
            folks = []
            for p in people:
                folks.append(p.__str__())
            if args.verbose:
                tqdm.write("Here are the people found:\n[")
                for f in folks:
                    tqdm.write(f)
                tqdm.write(f"]\n{len(folks)} people to be analyzed.")
            elif args.quiet:
                tqdm.write(f"{len(folks)} people.")
            else: 
                tqdm.write(f"{len(folks)} people have been found.")
            bigPic = tqdm(total=len(folks), desc="People", smoothing=0.6, unit="ppl", position=1, leave=False, maxinterval=3, mininterval=1)
            for p in people:
                searchingThroughFiles(fileList, args.pattern, args.verbose, args.separate,\
                    p.lastname, p.firstname, p.outputFile)
                bigPic.update(1)
            bigPic.close()
        else:
            searchingThroughFiles(fileList, args.pattern, args.verbose, \
                args.separate, args.name, args.firstname, args.output)
    else:
        tqdm.write(f"The option -l is not compatible with -n and -f")
    
            


if __name__ == "__main__":
    try:
        Main()
    except KeyboardInterrupt:
        tqdm.write("\n[ABORTED] Rage quit...\n")
end = datetime.datetime.now() - start

print(f"Total time: {str(end)}")