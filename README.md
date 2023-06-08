# ccdr-basic
ccdr-basic


Processing approach
-------------------

To process most required data (country dependent):

- run `dl.py` to download any required Aqueduct flooding layers. 
- run `preprocess.py` to generate all boundary and other layers required.
- run `hazards.py` to generate all hazard layers required.

To generate results and plots:

- run `demand.py` to produce population density and wealth decile plots.
- run `supply.py` to produce cell and fiber plots. 
- run `vuln.py` to produce vulnerability results for cells and fiber.

To visualize the results:

- Each R script generates the vulnerability metrics for each country (e.g., AZE.r).
-  


