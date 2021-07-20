#! /bin/sh 

git clone git@github.com:uncharted-causemos/docs.git

cd docs

#git checkout schema-update

cd ../

# One-off hack to delete unneeded ref
jq -r 'del(.["properties"]["model_id"]["$ref"])' ./docs/datacubes/model-run.schema.json > _.json && mv _.json ./docs/datacubes/model-run.schema.json
echo "Deleted External Reference"

# Read only "schema" jsons, not examples
files=`ls ./docs/datacubes/*schema*.json`

for file in $files
do
   fn=$file
   base_fn=${fn:17:$((${#fn} - 17 - 5))}

   #Indicator Schema
   if [[ "$base_fn" == "indicator.schema" ]]
       then
           echo "Converting $base_fn"	
           datamodel-codegen  --input $file --input-file-type jsonschema --output "validation/IndicatorSchema.py"
   fi

   # RUN SCHEMA
   if [[ "$base_fn" == "model-run.schema" ]]
       then
         echo "Converting $base_fn"
         datamodel-codegen  --input $file --input-file-type jsonschema --output "validation/RunSchema.py"
   fi

   # MODEL SCHEMA
   if [[ "$base_fn" == "model.schema" ]]
       then
           echo "Converting $base_fn"	
           datamodel-codegen  --input $file --input-file-type jsonschema --output "validation/ModelSchema.py"
   fi

done

# Delete cloned repo
rm -rf docs
