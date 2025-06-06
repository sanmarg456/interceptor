@echo off
cd "raw"
for %%f in (*.puml) do (
    java -jar %plant_uml% -tpng "%%f" -o "..\output"
)
echo Done