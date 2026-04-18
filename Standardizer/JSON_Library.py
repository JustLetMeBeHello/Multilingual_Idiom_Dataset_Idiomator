import json

def Structure_Senses(file_path, Output_File_Path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        grouped_data = {}
        data = json.load(json_file)
        for sense in data:
          #  print(sense)
            key = sense["idiom_id"]
            if key not in grouped_data:
                grouped_data[key] = [sense]
            else:
                grouped_data[key].append(sense)
        id = sense["idiom_id"]
        id_number = id[-3:]
       # print(grouped_data.items())
       # print(grouped_data.items)
        ranked_data = dict(sorted(grouped_data.items(), key = lambda x: int(x[0].split("_")[-1])))
        #print(list(ranked_data.values()))
      #  print(ranked_data.items())
        for idiom_id in grouped_data:
        #    ranked_data[item] = 
            i = 0
            for sense in grouped_data[idiom_id]:
                if sense["sense_number"] == 1:
                    i = i +1
                if i >= 2:
                    print(sense)  
        
        for idiom_id in ranked_data:
            
            #print(idiom_id)
            #print(ranked_data[idiom_id])
            ranked_data_idiom_id_copy = ranked_data[idiom_id].copy()
            for sense in ranked_data_idiom_id_copy:
                list = [1,2]
                if len(sense["definitions"]) > 1:
                    new_definitions = 0
                    registers = []
                    regions = []
                    for register_tag in sense["register"]:
                        register_tag = register_tag + "_tentative"
                        registers.append(register_tag)
                        if len(registers) == len(sense["register"]):
                            sense["register"] = registers
                            registers = []
                    for region in sense["region"]:
                        region = region + "_tentative"
                        regions.append(region)
                        if len(regions) == len(sense["region"]):
                            sense["region"] = regions
                            regions = []
                    for definition in sense["definitions"]:
                        new_sense = sense.copy()
                        if new_definitions == 0:
                            new_sense["sense_number"] = sense["sense_number"]  # keep original for first
                        else:
                            new_sense["sense_number"] = sense["sense_number"] + new_definitions  # offset, don't restart
                        new_definitions += 1
                        new_sense["definitions"] = definition
                        ranked_data[idiom_id].append(new_sense)
                    ranked_data[idiom_id].remove(sense)
                
            ranked_data[idiom_id] = sorted(ranked_data[idiom_id], key=lambda x: x["sense_number"])
            for idx, sense in enumerate(ranked_data[idiom_id], start=1):
                sense["sense_number"] = idx

        Sense_ranked_data = ranked_data

        with open(Output_File_Path, 'w', encoding = 'utf-8') as json_file:
                for idiom_id in Sense_ranked_data.items():
                    json.dump(idiom_id, json_file)
                    json_file.write("\n")
                #json.dump(Sense_ranked_data, json_file, indent=2)
                # the commented out method is for structured data while the base form is for flattened out dat

if __name__ == "__main__":
    name = "Telugu"
    Structure_Senses(f"idioms_structured/Idiom_meanings/Unlabelled_Meanings/{name}/Raw_Meanings_Unstructured.json",f"idioms_structured/Idiom_meanings/Unlabelled_Meanings/{name}/Raw_Meanings_Ordered_Flattened.jsonl")