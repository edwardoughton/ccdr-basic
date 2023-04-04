###VISUALISE MODEL OUTPUTS###
library(tidyverse)
library(ggpubr)

iso3 = 'AZE'

folder <- dirname(rstudioapi::getSourceEditorContext()$path)

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'data', 'processed', iso3, 'results', 'inunriver', 'fiber', 'csv_files', 'aggregated')
setwd(data_directory)

metric_files <- list.files(data_directory, pattern="inunriver")

empty_df <- data.frame(GID_1=character(),
                       length_m=numeric(), 
                       total_m=numeric(), 
                       cost_usd_low=numeric(),
                       cost_usd_baseline=numeric(),
                       cost_usd_high=numeric()
)

import_function = lapply(metric_files, function(x) {
  df <- read.csv(x, header = T, sep = ",")
  df_merge <- merge(empty_df, df, all = T)
  df_merge$file <- x
  return(df_merge)})

data <- do.call(rbind, import_function)

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'test.csv')
# write.csv(data, path)

rm(empty_df, import_function)

data = data %>%
  separate(file, 
           into = c(
             "hazard_type", 
             "climatescenario", 
             "subsidence_model", 
             "year", 
             "returnperiod",
             "zero",
             "perc",
             "percentile"), 
           sep = "_",
           convert = TRUE)

data$climatescenario = factor(data$climatescenario,
                              levels=c("historical","rcp4p5","rcp8p5"),
                              labels=c("Historical","RCP4.5","RCP8.5")
)
data$returnperiod = gsub(".csv", "", data$returnperiod)
data$returnperiod =  gsub("rp00025", "rp0025", data$returnperiod)
data$returnperiod =  gsub("rp00050", "rp0050", data$returnperiod)
data$returnperiod =  gsub("rp00100", "rp0100", data$returnperiod)
data$returnperiod =  gsub("rp00250", "rp0250", data$returnperiod)
data$returnperiod =  gsub("rp00500", "rp0500", data$returnperiod)
data$returnperiod =  gsub("rp01000", "rp1000", data$returnperiod)

data$probability = ''
# data$probability[data$returnperiod == "rp0002"] = "50%" # (1/2) * 100 = 50%
# data$probability[data$returnperiod == "rp0005"] = "20%" # (1/10) * 100 = 10%
data$probability[data$returnperiod == "rp0010"] = "10%" # (1/10) * 100 = 10%
data$probability[data$returnperiod == "rp0025"] = "4%" # (1/25) * 100 = 4%
data$probability[data$returnperiod == "rp0050"] = "2%" # (1/50) * 100 = 2%
data$probability[data$returnperiod == "rp0100"] = "1%" # (1/100) * 100 = 1%
data$probability[data$returnperiod == "rp0250"] = "0.4%" # (1/250) * 100 = .4%
data$probability[data$returnperiod == "rp0500"] = "0.2%" # (1/500) * 100 = .2%
data$probability[data$returnperiod == "rp1000"] = "0.1%" # (1/1000) * 100 = .1%

data$returnperiod = factor(data$returnperiod,
                           levels=c(
                             # "rp0002",
                             # "rp0005",
                             # "rp0010",
                             "rp0025",
                             "rp0050",
                             "rp0100",
                             "rp0250",
                             "rp0500",
                             "rp1000"
                           ),
                           labels=c(
                             # "1-in-2-Years",
                             # "1-in-5-Years",
                             # "1-in-10-Years",
                             "1-in-25-Years",
                             "1-in-50-Years",
                             "1-in-100-Years",
                             "1-in-250-Years",
                             "1-in-500-Years",
                             "1-in-1000-Years"
                           )
)

data$probability = factor(data$probability,
                          levels=c(
                            "0.1%",
                            "0.2%",
                            "0.4%",
                            "1%",
                            "2%",
                            "4%"#,
                            # "10%",
                            # "20%",
                            # "50%"
                          )
)
# 
# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'data.csv')
# write.csv(data, path)

#average across all models
data_aggregated  = data %>%
  group_by(GID_1, year, climatescenario, probability, returnperiod) %>%
  summarise(
    length_m = mean(length_m),
    # total_m = mean(total_m),
    cost_usd_low = mean(cost_usd_low),
    cost_usd_baseline = mean(cost_usd_baseline),
    cost_usd_high = mean(cost_usd_high),
  )

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'mean_regional_direct_costs.csv')
# write.csv(data_aggregated, path)

#sum across all lower regions to the national level
data_aggregated  = data_aggregated %>%
  group_by(year, climatescenario, probability, returnperiod) %>%
  summarise(
    cost_usd_low = sum(cost_usd_low)/1e6,
    cost_usd_baseline = sum(cost_usd_baseline)/1e6,
    cost_usd_high = sum(cost_usd_high)/1e6,
  )

max_y_value = max(data_aggregated$cost_usd_high, na.rm = TRUE)

plot1 = ggplot(data_aggregated, 
         aes(x=probability, y=cost_usd_baseline, fill=climatescenario)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_errorbar(data=data_aggregated, aes(
    y=cost_usd_baseline, ymin=cost_usd_low, ymax=cost_usd_high),
                position = position_dodge(1),
                lwd = 0.2,
                show.legend = FALSE, width=0.1,  color="#FF0000FF") +
  geom_text(aes(label = paste(round(cost_usd_baseline,2),"Mn")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.2, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Direct Damage Cost to Fiber Networks in Azerbaijan",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Direct Damage (US$ Millions)", fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) #+

path = file.path(folder, 'figures', iso3, 'AZE_direct_damage_fiber.png')
ggsave(path, units="in", width=8, height=6, dpi=300)


######
######
######
iso3 = 'AZE'

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'data', 'processed', iso3, 'results', 'inunriver', 'fiber', 'csv_files')
setwd(data_directory)

data <- read.csv('inunriver_aggregated_results.csv', header = T, sep = ",")

data$scenario = factor(data$scenario,
                              levels=c("historical","rcp4p5","rcp8p5"),
                              labels=c("Historical","RCP4.5","RCP8.5")
)

data$return_period =  gsub("rp00025", "rp0025", data$return_period)
data$return_period =  gsub("rp00050", "rp0050", data$return_period)
data$return_period =  gsub("rp00100", "rp0100", data$return_period)
data$return_period =  gsub("rp00250", "rp0250", data$return_period)
data$return_period =  gsub("rp00500", "rp0500", data$return_period)
data$return_period =  gsub("rp01000", "rp1000", data$return_period)

data$probability = ''
# data$probability[data$returnperiod == "rp0002"] = "50%" # (1/2) * 100 = 50%
# data$probability[data$returnperiod == "rp0005"] = "20%" # (1/10) * 100 = 10%
data$probability[data$return_period == "rp0010"] = "10%" # (1/10) * 100 = 10%
data$probability[data$return_period == "rp0025"] = "4%" # (1/25) * 100 = 4%
data$probability[data$return_period == "rp0050"] = "2%" # (1/50) * 100 = 2%
data$probability[data$return_period == "rp0100"] = "1%" # (1/100) * 100 = 1%
data$probability[data$return_period == "rp0250"] = "0.4%" # (1/250) * 100 = .4%
data$probability[data$return_period == "rp0500"] = "0.2%" # (1/500) * 100 = .2%
data$probability[data$return_period == "rp1000"] = "0.1%" # (1/1000) * 100 = .1%

data$return_period = factor(data$return_period,
                           levels=c(
                             # "rp0002",
                             # "rp0005",
                             # "rp0010",
                             "rp0025",
                             "rp0050",
                             "rp0100",
                             "rp0250",
                             "rp0500",
                             "rp1000"
                           ),
                           labels=c(
                             # "1-in-2-Years",
                             # "1-in-5-Years",
                             # "1-in-10-Years",
                             "1-in-25-Years",
                             "1-in-50-Years",
                             "1-in-100-Years",
                             "1-in-250-Years",
                             "1-in-500-Years",
                             "1-in-1000-Years"
                           )
)

data$probability = factor(data$probability,
                          levels=c(
                            "0.1%",
                            "0.2%",
                            "0.4%",
                            "1%",
                            "2%",
                            "4%"#,
                            # "10%",
                            # "20%",
                            # "50%"
                          )
)

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'aggregated_fiber_damage.csv')
# write.csv(data, path)

#average across all models
data_aggregated  = data %>%
  group_by(scenario, probability, return_period) %>%
  summarise(
    fiber_at_risk_km_min = min(fiber_at_risk_km),
    fiber_at_risk_perc_min = min(fiber_at_risk_perc),
    
    fiber_at_risk_km_mean = mean(fiber_at_risk_km),
    fiber_at_risk_perc_mean = mean(fiber_at_risk_perc),
    
    fiber_at_risk_km_max = max(fiber_at_risk_km),
    fiber_at_risk_perc_max = max(fiber_at_risk_perc),
  )

max_y_value = max(data_aggregated$fiber_at_risk_perc_max, na.rm = TRUE)

 plot1 = 
  ggplot(data_aggregated, aes(x=probability, y=fiber_at_risk_perc_mean, fill=scenario)) + 
    geom_bar(stat="identity", position = position_dodge()) +
  geom_errorbar(data=data_aggregated, aes(
    y=fiber_at_risk_perc_mean, ymin=fiber_at_risk_perc_min, ymax=fiber_at_risk_perc_max),
    position = position_dodge(1),
    lwd = 0.2,
    show.legend = FALSE, width=0.1,  color="#FF0000FF") +
  geom_text(aes(label = paste(round(fiber_at_risk_perc_mean,1),"")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Damage to Fiber Networks in Azerbaijan",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Fiber at Risk (%)", fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) #+

 
 # #average across all models
 # data_aggregated  = data %>%
 #   group_by(scenario, probability, return_period) %>%
 #   summarise(
 #     fiber_at_risk_km_min = min(fiber_at_risk_km),
 #     fiber_at_risk_perc_min = min(fiber_at_risk_perc),
 #     
 #     fiber_at_risk_km_mean = mean(fiber_at_risk_km),
 #     fiber_at_risk_perc_mean = mean(fiber_at_risk_perc),
 #     
 #     fiber_at_risk_km_max = max(fiber_at_risk_km),
 #     fiber_at_risk_perc_max = max(fiber_at_risk_perc),
 #   )
 # 
 
 max_y_value = max(data_aggregated$fiber_at_risk_km_max, na.rm = TRUE)
 
 plot2 = 
   ggplot(data_aggregated, aes(x=probability, y=fiber_at_risk_km_mean, fill=scenario)) + 
   geom_bar(stat="identity", position = position_dodge()) +
   geom_errorbar(data=data_aggregated, aes(
     y=fiber_at_risk_km_mean, ymin=fiber_at_risk_km_min, ymax=fiber_at_risk_km_max),
     position = position_dodge(1),
     lwd = 0.2,
     show.legend = FALSE, width=0.1,  color="#FF0000FF") +
   geom_text(aes(label = paste(round(fiber_at_risk_km_mean,0),"")), size = 1.8,
             position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
   theme(legend.position = 'bottom',
         axis.text.x = element_text(angle=45, hjust=1)) +
   labs(colour=NULL,
        title = "Estimated Riverine Flooding Damage to Fiber Networks in Azerbaijan",
        subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
        x = "Annual Probability of Occurance (%)", y = "Fiber at Risk (km)", fill="Climate Scenario") +
   theme(panel.spacing = unit(0.6, "lines")) + 
   expand_limits(y=0) +
   guides(fill=guide_legend(ncol=3, title='Scenario')) +
   scale_fill_viridis_d(direction=1) +
   scale_x_discrete(expand = c(0, 0.15)) +
   scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) #+
 
ggarrange(
   plot1, 
   plot2, 
   labels = c("A", "B"),
   common.legend = TRUE,
   legend = 'bottom',
   ncol = 1, nrow = 2)
 
path = file.path(folder, 'figures', iso3, 'AZE_fiber_at_risk.png')
ggsave(path, units="in", width=8, height=6, dpi=300)

###########
###########
###########

iso3 = 'AZE'

folder <- dirname(rstudioapi::getSourceEditorContext()$path)

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'data', 'processed', iso3, 'results', 'inunriver', 'cells', 'csv_files', 'aggregated')
setwd(data_directory)

metric_files <- list.files(data_directory, pattern="inunriver")

empty_df <- data.frame(GID_1=character(),
                       radio=character(), 
                       cell_count=numeric(), 
                       cost_usd_low=numeric(),
                       cost_usd_baseline=numeric(),
                       cost_usd_high=numeric()
)

import_function = lapply(metric_files, function(x) {
  df <- read.csv(x, header = T, sep = ",")
  df_merge <- merge(empty_df, df, all = T)
  df_merge$file <- x
  return(df_merge)})

data <- do.call(rbind, import_function)

folder_out = file.path(folder, 'data', iso3)
dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
path = file.path(folder_out, 'test.csv')
write.csv(data, path)

rm(empty_df, import_function)

data = data %>%
  separate(file, 
           into = c(
             "hazard_type", 
             "climatescenario", 
             "subsidence_model", 
             "year", 
             "returnperiod",
             "zero",
             "perc",
             "percentile"), 
           sep = "_",
           convert = TRUE)

data$climatescenario = factor(data$climatescenario,
                              levels=c("historical","rcp4p5","rcp8p5"),
                              labels=c("Historical","RCP4.5","RCP8.5")
)
data$returnperiod = gsub(".csv", "", data$returnperiod)
data$returnperiod =  gsub("rp00025", "rp0025", data$returnperiod)
data$returnperiod =  gsub("rp00050", "rp0050", data$returnperiod)
data$returnperiod =  gsub("rp00100", "rp0100", data$returnperiod)
data$returnperiod =  gsub("rp00250", "rp0250", data$returnperiod)
data$returnperiod =  gsub("rp00500", "rp0500", data$returnperiod)
data$returnperiod =  gsub("rp01000", "rp1000", data$returnperiod)

data$probability = ''
# data$probability[data$returnperiod == "rp0002"] = "50%" # (1/2) * 100 = 50%
# data$probability[data$returnperiod == "rp0005"] = "20%" # (1/10) * 100 = 10%
data$probability[data$returnperiod == "rp0010"] = "10%" # (1/10) * 100 = 10%
data$probability[data$returnperiod == "rp0025"] = "4%" # (1/25) * 100 = 4%
data$probability[data$returnperiod == "rp0050"] = "2%" # (1/50) * 100 = 2%
data$probability[data$returnperiod == "rp0100"] = "1%" # (1/100) * 100 = 1%
data$probability[data$returnperiod == "rp0250"] = "0.4%" # (1/250) * 100 = .4%
data$probability[data$returnperiod == "rp0500"] = "0.2%" # (1/500) * 100 = .2%
data$probability[data$returnperiod == "rp1000"] = "0.1%" # (1/1000) * 100 = .1%

data$returnperiod = factor(data$returnperiod,
                           levels=c(
                             # "rp0002",
                             # "rp0005",
                             # "rp0010",
                             "rp0025",
                             "rp0050",
                             "rp0100",
                             "rp0250",
                             "rp0500",
                             "rp1000"
                           ),
                           labels=c(
                             # "1-in-2-Years",
                             # "1-in-5-Years",
                             # "1-in-10-Years",
                             "1-in-25-Years",
                             "1-in-50-Years",
                             "1-in-100-Years",
                             "1-in-250-Years",
                             "1-in-500-Years",
                             "1-in-1000-Years"
                           )
)

data$probability = factor(data$probability,
                          levels=c(
                            "0.1%",
                            "0.2%",
                            "0.4%",
                            "1%",
                            "2%",
                            "4%"#,
                            # "10%",
                            # "20%",
                            # "50%"
                          )
)

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'data.csv')
# write.csv(data, path)

#average across all models
data_aggregated  = data %>%
  group_by(GID_1, year, climatescenario, probability, returnperiod) %>%
  summarise(
    cell_count = round(mean(cell_count)),
    # total_m = mean(total_m),
    cost_usd_low = mean(cost_usd_low),
    cost_usd_baseline = mean(cost_usd_baseline),
    cost_usd_high = mean(cost_usd_high),
  )

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'mean_regional_direct_costs.csv')
# write.csv(data_aggregated, path)

#sum across all lower regions to the national level
data_aggregated  = data_aggregated %>%
  group_by(year, climatescenario, probability, returnperiod) %>%
  summarise(
    cost_usd_low = sum(cost_usd_low)/1e6,
    cost_usd_baseline = sum(cost_usd_baseline)/1e6,
    cost_usd_high = sum(cost_usd_high)/1e6,
  )

max_y_value = max(data_aggregated$cost_usd_high, na.rm = TRUE)

plot1 = ggplot(data_aggregated, 
               aes(x=probability, y=cost_usd_baseline, fill=climatescenario)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_errorbar(data=data_aggregated, aes(
    y=cost_usd_baseline, ymin=cost_usd_low, ymax=cost_usd_high),
    position = position_dodge(1),
    lwd = 0.2,
    show.legend = FALSE, width=0.1,  color="#FF0000FF") +
  geom_text(aes(label = paste(round(cost_usd_baseline,2),"Mn")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.2, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Direct Damage Cost to Mobile Cells in Azerbaijan",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Direct Damage (US$ Millions)", 
       fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) #+

path = file.path(folder, 'figures', iso3, 'AZE_direct_damage_cells.png')
ggsave(path, units="in", width=8, height=6, dpi=300)

######
######
######

iso3 = 'AZE'

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'data', 'processed', iso3, 'results', 'inunriver', 'cells', 'csv_files')
setwd(data_directory)

data <- read.csv('inunriver_aggregated_results.csv', header = T, sep = ",")

data$scenario = factor(data$scenario,
                       levels=c("historical","rcp4p5","rcp8p5"),
                       labels=c("Historical","RCP4.5","RCP8.5")
)

data$return_period =  gsub("rp00025", "rp0025", data$return_period)
data$return_period =  gsub("rp00050", "rp0050", data$return_period)
data$return_period =  gsub("rp00100", "rp0100", data$return_period)
data$return_period =  gsub("rp00250", "rp0250", data$return_period)
data$return_period =  gsub("rp00500", "rp0500", data$return_period)
data$return_period =  gsub("rp01000", "rp1000", data$return_period)

data$probability = ''
# data$probability[data$returnperiod == "rp0002"] = "50%" # (1/2) * 100 = 50%
# data$probability[data$returnperiod == "rp0005"] = "20%" # (1/10) * 100 = 10%
data$probability[data$return_period == "rp0010"] = "10%" # (1/10) * 100 = 10%
data$probability[data$return_period == "rp0025"] = "4%" # (1/25) * 100 = 4%
data$probability[data$return_period == "rp0050"] = "2%" # (1/50) * 100 = 2%
data$probability[data$return_period == "rp0100"] = "1%" # (1/100) * 100 = 1%
data$probability[data$return_period == "rp0250"] = "0.4%" # (1/250) * 100 = .4%
data$probability[data$return_period == "rp0500"] = "0.2%" # (1/500) * 100 = .2%
data$probability[data$return_period == "rp1000"] = "0.1%" # (1/1000) * 100 = .1%

data$return_period = factor(data$return_period,
                            levels=c(
                              # "rp0002",
                              # "rp0005",
                              # "rp0010",
                              "rp0025",
                              "rp0050",
                              "rp0100",
                              "rp0250",
                              "rp0500",
                              "rp1000"
                            ),
                            labels=c(
                              # "1-in-2-Years",
                              # "1-in-5-Years",
                              # "1-in-10-Years",
                              "1-in-25-Years",
                              "1-in-50-Years",
                              "1-in-100-Years",
                              "1-in-250-Years",
                              "1-in-500-Years",
                              "1-in-1000-Years"
                            )
)

data$probability = factor(data$probability,
                          levels=c(
                            "0.1%",
                            "0.2%",
                            "0.4%",
                            "1%",
                            "2%",
                            "4%"#,
                            # "10%",
                            # "20%",
                            # "50%"
                          )
)

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'aggregated_fiber_damage.csv')
# write.csv(data, path)

data = data %>%
  group_by(scenario, probability, return_period, year, model) %>%
  summarise(
    cells_at_risk = sum(cells_at_risk),
    total_cells = sum(total_cells),
    cells_at_risk_perc = round((sum(cells_at_risk)/sum(total_cells))*100, 2)
  )

#average across all models
data_aggregated  = data %>%
  group_by(scenario, probability, return_period) %>%
  summarise(
    cells_at_risk_min = round(min(cells_at_risk)),
    cells_at_risk_perc_min = min(cells_at_risk_perc),
    
    cells_at_risk_mean = round(mean(cells_at_risk)),
    cells_at_risk_perc_mean = mean(cells_at_risk_perc),
    
    cells_at_risk_max = round(max(cells_at_risk)),
    cells_at_risk_perc_max = max(cells_at_risk_perc),
  )

max_y_value = max(data_aggregated$cells_at_risk_perc_max, na.rm = TRUE)

plot1 = 
  ggplot(data_aggregated, aes(x=probability, y=cells_at_risk_perc_mean, fill=scenario)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_errorbar(data=data_aggregated, aes(
    y=cells_at_risk_perc_mean, ymin=cells_at_risk_perc_min, ymax=cells_at_risk_perc_max),
    position = position_dodge(1),
    lwd = 0.2,
    show.legend = FALSE, width=0.1,  color="#FF0000FF") +
  geom_text(aes(label = paste(round(cells_at_risk_perc_mean,2),"")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Damage to Mobile Cells in Azerbaijan",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Mobile Cells at Risk (%)", fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) #+


# #average across all models
# data_aggregated  = data %>%
#   group_by(scenario, probability, return_period) %>%
#   summarise(
#     fiber_at_risk_km_min = min(fiber_at_risk_km),
#     fiber_at_risk_perc_min = min(fiber_at_risk_perc),
#     
#     fiber_at_risk_km_mean = mean(fiber_at_risk_km),
#     fiber_at_risk_perc_mean = mean(fiber_at_risk_perc),
#     
#     fiber_at_risk_km_max = max(fiber_at_risk_km),
#     fiber_at_risk_perc_max = max(fiber_at_risk_perc),
#   )
# 

max_y_value = max(data_aggregated$cells_at_risk_max, na.rm = TRUE)

plot2 = 
  ggplot(data_aggregated, aes(x=probability, y=cells_at_risk_mean, fill=scenario)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_errorbar(data=data_aggregated, aes(
    y=cells_at_risk_mean, ymin=cells_at_risk_min, ymax=cells_at_risk_max),
    position = position_dodge(1),
    lwd = 0.2,
    show.legend = FALSE, width=0.1,  color="#FF0000FF") +
  geom_text(aes(label = paste(round(cells_at_risk_mean,0),"")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Damage to Mobile Cells in Azerbaijan",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Mobile Cells at Risk", 
       fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) 

ggarrange(
  plot1, 
  plot2, 
  labels = c("A", "B"),
  common.legend = TRUE,
  legend = 'bottom',
  ncol = 1, nrow = 2)

path = file.path(folder, 'figures', iso3, 'AZE_cells_at_risk.png')
ggsave(path, units="in", width=8, height=6, dpi=300)









###########
###########
###########

iso3 = 'AZE'

folder <- dirname(rstudioapi::getSourceEditorContext()$path)

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'data', 'processed', iso3, 'results', 'inunriver', 'roads', 'csv_files', 'aggregated')
setwd(data_directory)

metric_files <- list.files(data_directory, pattern="inunriver")

empty_df <- data.frame(GID_1=character(),
                       # radio=character(), 
                       length_m=numeric(), 
                       cost_usd_low=numeric(),
                       cost_usd_baseline=numeric(),
                       cost_usd_high=numeric()
)

import_function = lapply(metric_files, function(x) {
  df <- read.csv(x, header = T, sep = ",")
  df_merge <- merge(empty_df, df, all = T)
  df_merge$file <- x
  return(df_merge)})

data <- do.call(rbind, import_function)
# 
# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'test.csv')
# write.csv(data, path)

rm(empty_df, import_function)

data = data %>%
  separate(file, 
           into = c(
             "hazard_type", 
             "climatescenario", 
             "subsidence_model", 
             "year", 
             "returnperiod",
             "zero",
             "perc",
             "percentile"), 
           sep = "_",
           convert = TRUE)

data$climatescenario = factor(data$climatescenario,
                              levels=c("historical","rcp4p5","rcp8p5"),
                              labels=c("Historical","RCP4.5","RCP8.5")
)
data$returnperiod = gsub(".csv", "", data$returnperiod)
data$returnperiod =  gsub("rp00025", "rp0025", data$returnperiod)
data$returnperiod =  gsub("rp00050", "rp0050", data$returnperiod)
data$returnperiod =  gsub("rp00100", "rp0100", data$returnperiod)
data$returnperiod =  gsub("rp00250", "rp0250", data$returnperiod)
data$returnperiod =  gsub("rp00500", "rp0500", data$returnperiod)
data$returnperiod =  gsub("rp01000", "rp1000", data$returnperiod)

data$probability = ''
# data$probability[data$returnperiod == "rp0002"] = "50%" # (1/2) * 100 = 50%
# data$probability[data$returnperiod == "rp0005"] = "20%" # (1/10) * 100 = 10%
data$probability[data$returnperiod == "rp0010"] = "10%" # (1/10) * 100 = 10%
data$probability[data$returnperiod == "rp0025"] = "4%" # (1/25) * 100 = 4%
data$probability[data$returnperiod == "rp0050"] = "2%" # (1/50) * 100 = 2%
data$probability[data$returnperiod == "rp0100"] = "1%" # (1/100) * 100 = 1%
data$probability[data$returnperiod == "rp0250"] = "0.4%" # (1/250) * 100 = .4%
data$probability[data$returnperiod == "rp0500"] = "0.2%" # (1/500) * 100 = .2%
data$probability[data$returnperiod == "rp1000"] = "0.1%" # (1/1000) * 100 = .1%

data$returnperiod = factor(data$returnperiod,
                           levels=c(
                             # "rp0002",
                             # "rp0005",
                             # "rp0010",
                             "rp0025",
                             "rp0050",
                             "rp0100",
                             "rp0250",
                             "rp0500",
                             "rp1000"
                           ),
                           labels=c(
                             # "1-in-2-Years",
                             # "1-in-5-Years",
                             # "1-in-10-Years",
                             "1-in-25-Years",
                             "1-in-50-Years",
                             "1-in-100-Years",
                             "1-in-250-Years",
                             "1-in-500-Years",
                             "1-in-1000-Years"
                           )
)

data$probability = factor(data$probability,
                          levels=c(
                            "0.1%",
                            "0.2%",
                            "0.4%",
                            "1%",
                            "2%",
                            "4%"#,
                            # "10%",
                            # "20%",
                            # "50%"
                          )
)

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'data.csv')
# write.csv(data, path)

#average across all models
data_aggregated  = data %>%
  group_by(GID_1, year, climatescenario, probability, returnperiod) %>%
  summarise(
    length_m = round(mean(length_m)),
    # total_m = mean(total_m),
    cost_usd_low = mean(cost_usd_low),
    cost_usd_baseline = mean(cost_usd_baseline),
    cost_usd_high = mean(cost_usd_high),
  )

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'mean_regional_direct_costs.csv')
# write.csv(data_aggregated, path)

#sum across all lower regions to the national level
data_aggregated  = data_aggregated %>%
  group_by(year, climatescenario, probability, returnperiod) %>%
  summarise(
    cost_usd_low = sum(cost_usd_low)/1e6,
    cost_usd_baseline = sum(cost_usd_baseline)/1e6,
    cost_usd_high = sum(cost_usd_high)/1e6,
  )

max_y_value = max(data_aggregated$cost_usd_high, na.rm = TRUE)

plot1 = ggplot(data_aggregated, 
               aes(x=probability, y=cost_usd_baseline, fill=climatescenario)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_errorbar(data=data_aggregated, aes(
    y=cost_usd_baseline, ymin=cost_usd_low, ymax=cost_usd_high),
    position = position_dodge(1),
    lwd = 0.2,
    show.legend = FALSE, width=0.1,  color="#FF0000FF") +
  geom_text(aes(label = paste(round(cost_usd_baseline,0),"Mn")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.2, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Direct Damage Cost to Roads in Azerbaijan",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Direct Damage (US$ Millions)", 
       fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) #+

path = file.path(folder, 'figures', iso3, 'AZE_direct_damage_roads.png')
ggsave(path, units="in", width=8, height=6, dpi=300)

######
######
######

iso3 = 'AZE'

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'data', 'processed', iso3, 'results', 'inunriver', 'roads', 'csv_files')
setwd(data_directory)

data <- read.csv('inunriver_aggregated_results.csv', header = T, sep = ",")

data$scenario = factor(data$scenario,
                       levels=c("historical","rcp4p5","rcp8p5"),
                       labels=c("Historical","RCP4.5","RCP8.5")
)

data$return_period =  gsub("rp00025", "rp0025", data$return_period)
data$return_period =  gsub("rp00050", "rp0050", data$return_period)
data$return_period =  gsub("rp00100", "rp0100", data$return_period)
data$return_period =  gsub("rp00250", "rp0250", data$return_period)
data$return_period =  gsub("rp00500", "rp0500", data$return_period)
data$return_period =  gsub("rp01000", "rp1000", data$return_period)

data$probability = ''
# data$probability[data$returnperiod == "rp0002"] = "50%" # (1/2) * 100 = 50%
# data$probability[data$returnperiod == "rp0005"] = "20%" # (1/10) * 100 = 10%
data$probability[data$return_period == "rp0010"] = "10%" # (1/10) * 100 = 10%
data$probability[data$return_period == "rp0025"] = "4%" # (1/25) * 100 = 4%
data$probability[data$return_period == "rp0050"] = "2%" # (1/50) * 100 = 2%
data$probability[data$return_period == "rp0100"] = "1%" # (1/100) * 100 = 1%
data$probability[data$return_period == "rp0250"] = "0.4%" # (1/250) * 100 = .4%
data$probability[data$return_period == "rp0500"] = "0.2%" # (1/500) * 100 = .2%
data$probability[data$return_period == "rp1000"] = "0.1%" # (1/1000) * 100 = .1%

data$return_period = factor(data$return_period,
                            levels=c(
                              # "rp0002",
                              # "rp0005",
                              # "rp0010",
                              "rp0025",
                              "rp0050",
                              "rp0100",
                              "rp0250",
                              "rp0500",
                              "rp1000"
                            ),
                            labels=c(
                              # "1-in-2-Years",
                              # "1-in-5-Years",
                              # "1-in-10-Years",
                              "1-in-25-Years",
                              "1-in-50-Years",
                              "1-in-100-Years",
                              "1-in-250-Years",
                              "1-in-500-Years",
                              "1-in-1000-Years"
                            )
)

data$probability = factor(data$probability,
                          levels=c(
                            "0.1%",
                            "0.2%",
                            "0.4%",
                            "1%",
                            "2%",
                            "4%"#,
                            # "10%",
                            # "20%",
                            # "50%"
                          )
)

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'aggregated_fiber_damage.csv')
# write.csv(data, path)

data = data %>%
  group_by(scenario, probability, return_period, year, model) %>%
  summarise(
    road_at_risk_km = sum(road_at_risk_km),
    total_road_km = sum(total_road_km),
    road_at_risk_km_perc = round((sum(road_at_risk_km)/sum(total_road_km))*100, 2)
  )

#average across all models
data_aggregated  = data %>%
  group_by(scenario, probability, return_period) %>%
  summarise(
    road_at_risk_km_min = round(min(road_at_risk_km)),
    road_at_risk_km_perc_min = min(road_at_risk_km_perc),
    
    road_at_risk_km_mean = round(mean(road_at_risk_km)),
    road_at_risk_km_perc_mean = mean(road_at_risk_km_perc),
    
    road_at_risk_km_max = round(max(road_at_risk_km)),
    road_at_risk_km_perc_max = max(road_at_risk_km_perc),
  )

max_y_value = max(data_aggregated$road_at_risk_km_perc_max, na.rm = TRUE)

plot1 = 
  ggplot(data_aggregated, aes(x=probability, y=road_at_risk_km_perc_mean, fill=scenario)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_errorbar(data=data_aggregated, aes(
    y=road_at_risk_km_perc_mean, ymin=road_at_risk_km_perc_min, ymax=road_at_risk_km_perc_max),
    position = position_dodge(1),
    lwd = 0.2,
    show.legend = FALSE, width=0.1,  color="#FF0000FF") +
  geom_text(aes(label = paste(round(road_at_risk_km_perc_mean,2),"")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Damage to Roads in Azerbaijan",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Roads at Risk (%)", fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) #+


# #average across all models
# data_aggregated  = data %>%
#   group_by(scenario, probability, return_period) %>%
#   summarise(
#     fiber_at_risk_km_min = min(fiber_at_risk_km),
#     fiber_at_risk_perc_min = min(fiber_at_risk_perc),
#     
#     fiber_at_risk_km_mean = mean(fiber_at_risk_km),
#     fiber_at_risk_perc_mean = mean(fiber_at_risk_perc),
#     
#     fiber_at_risk_km_max = max(fiber_at_risk_km),
#     fiber_at_risk_perc_max = max(fiber_at_risk_perc),
#   )
# 

max_y_value = max(data_aggregated$road_at_risk_km_max, na.rm = TRUE)

plot2 = 
  ggplot(data_aggregated, aes(x=probability, y=road_at_risk_km_mean, fill=scenario)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_errorbar(data=data_aggregated, aes(
    y=road_at_risk_km_mean, ymin=road_at_risk_km_min, ymax=road_at_risk_km_max),
    position = position_dodge(1),
    lwd = 0.2,
    show.legend = FALSE, width=0.1,  color="#FF0000FF") +
  geom_text(aes(label = paste(round(road_at_risk_km_mean,0),"")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Damage to Roads in Azerbaijan",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Roads at Risk (km)", 
       fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) 

ggarrange(
  plot1, 
  plot2, 
  labels = c("A", "B"),
  common.legend = TRUE,
  legend = 'bottom',
  ncol = 1, nrow = 2)

path = file.path(folder, 'figures', iso3, 'AZE_roads_at_risk.png')
ggsave(path, units="in", width=8, height=6, dpi=300)

