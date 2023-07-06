###VISUALISE MODEL OUTPUTS###
# install.packages("tidyverse")
library(tidyverse)
# install.packages("ggpubr")
library(ggpubr)

iso3 = 'KEN'

folder <- dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3,  'inunriver', 'fiber', 'csv_files', 'aggregated')
setwd(data_directory)

metric_files <- list.files(data_directory, pattern="inunriver")

empty_df <- data.frame(GID_1=character(),
                       length_m=numeric(), 
                       # total_m=numeric(), 
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
       title = "Estimated Riverine Flooding Direct Damage Cost to Fiber Networks in Kenya",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Direct Damage (US$ Millions)", 
       fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/8))) #+

path = file.path(folder, 'figures', iso3, paste(iso3,'_direct_damage_fiber.png'))
ggsave(path, units="in", width=8, height=6, dpi=300)


######
######
######
iso3 = 'KEN'

folder <- dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3,  'inunriver', 'fiber', 'csv_files')
setwd(data_directory)

data <- read.csv('inunriver_aggregated_results.csv', header = T, sep = ",")

data = data %>%
  separate(filename, 
           into = c(
             "hazard_type", 
             "scenario", 
             "subsidence_model", 
             "year", 
             "return_period",
             "zero",
             "perc",
             "percentile"), 
           sep = "_",
           convert = TRUE)

data$return_period = gsub('.csv','', data$return_period)

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
  geom_text(aes(label = paste(round(fiber_at_risk_perc_mean,2),"")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Damage to Fiber Networks in Kenya",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Fiber at Risk (%)", fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/5))) #+

 
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
   geom_text(aes(label = paste(round(fiber_at_risk_km_mean,1),"")), size = 1.8,
             position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
   theme(legend.position = 'bottom',
         axis.text.x = element_text(angle=45, hjust=1)) +
   labs(colour=NULL,
        title = "Estimated Riverine Flooding Damage to Fiber Networks in Kenya",
        subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
        x = "Annual Probability of Occurance (%)", y = "Fiber at Risk (km)", fill="Climate Scenario") +
   theme(panel.spacing = unit(0.6, "lines")) + 
   expand_limits(y=0) +
   guides(fill=guide_legend(ncol=3, title='Scenario')) +
   scale_fill_viridis_d(direction=1) +
   scale_x_discrete(expand = c(0, 0.15)) +
   scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/5))) #+
 
ggarrange(
   plot1, 
   plot2, 
   labels = c("A", "B"),
   common.legend = TRUE,
   legend = 'bottom',
   ncol = 1, nrow = 2)
 
path = file.path(folder, 'figures', iso3, paste(iso3,'_fiber_at_risk.png'))
ggsave(path, units="in", width=8, height=6, dpi=300)

###########
###########
###########

iso3 = 'KEN'

folder <- dirname(rstudioapi::getSourceEditorContext()$path)

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3, 'inunriver', 'cells', 'csv_files', 'aggregated')
setwd(data_directory)

metric_files <- list.files(data_directory, pattern="inunriver")

empty_df <- data.frame(GID_1=character(),
                       # radio=character(), 
                       # cell_count=numeric(), 
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
    count = mean(count),
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
  geom_text(aes(label = paste(round(cost_usd_baseline,1),"Mn")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.2, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Direct Damage Cost to Fiber Networks in Kenya",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Direct Damage (US$ Millions)", fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) #+

path = file.path(folder, 'figures', iso3, paste(iso3,'_direct_damage_cells.png'))
ggsave(path, units="in", width=8, height=6, dpi=300)


######
######
######
iso3 = 'KEN'

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3, 'inunriver', 'fiber', 'csv_files')
setwd(data_directory)

data <- read.csv('inunriver_aggregated_results.csv', header = T, sep = ",")

data = data %>%
  separate(filename, 
           into = c(
             "hazard_type", 
             "scenario", 
             "subsidence_model", 
             "year", 
             "return_period",
             "zero",
             "perc",
             "percentile"), 
           sep = "_",
           convert = TRUE)

data$return_period = gsub('.csv','', data$return_period)

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
       title = "Estimated Riverine Flooding Damage to Fiber Networks in Kenya",
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
   geom_text(aes(label = paste(round(fiber_at_risk_km_mean,1),"")), size = 1.8,
             position = position_dodge(1), vjust =-.5, hjust =-.7, angle = 0)+
   theme(legend.position = 'bottom',
         axis.text.x = element_text(angle=45, hjust=1)) +
   labs(colour=NULL,
        title = "Estimated Riverine Flooding Damage to Fiber Networks in Kenya",
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
 
path = file.path(folder, 'figures', iso3, paste(iso3,'_fiber_at_risk.png'))
ggsave(path, units="in", width=8, height=6, dpi=300)

###########
###########
###########

iso3 = 'KEN'

folder <- dirname(rstudioapi::getSourceEditorContext()$path)

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3, 'inunriver', 'cells', 'csv_files', 'aggregated')
setwd(data_directory)

metric_files <- list.files(data_directory, pattern="inunriver")

empty_df <- data.frame(GID_1=character(),
                       # radio=character(), 
                       count=numeric(), 
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

# folder_out = file.path(folder, 'data', iso3)
# dir.create(folder_out, showWarnings = FALSE, recursive = TRUE)
# path = file.path(folder_out, 'data.csv')
# write.csv(data, path)

#average across all models
data_aggregated  = data %>%
  group_by(GID_1, year, climatescenario, probability, returnperiod) %>%
  summarise(
    cell_count = round(mean(count)),
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
data_aggregated = data_aggregated %>%
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
  geom_text(aes(label = paste(round(cost_usd_baseline,1),"Mn")), size = 1.8,
            position = position_dodge(1), vjust =-.5, hjust =-.2, angle = 0)+
  theme(legend.position = 'bottom',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Riverine Flooding Direct Damage Cost to Mobile Cells in Kenya",
       subtitle = "Reported by Annual Probability and Climate Scenario for 2080.", 
       x = "Annual Probability of Occurance (%)", y = "Direct Damage (US$ Millions)", 
       fill="Climate Scenario") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/8))) #+

path = file.path(folder, 'figures', iso3, paste(iso3,'_direct_damage_cells.png'))
ggsave(path, units="in", width=8, height=6, dpi=300)

######
######
######

iso3 = 'KEN'

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3, 'inunriver', 'cells', 'csv_files')
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
       title = "Estimated Riverine Flooding Damage to Mobile Cells in Kenya",
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
       title = "Estimated Riverine Flooding Damage to Mobile Cells in Kenya",
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

path = file.path(folder, 'figures', iso3, paste(iso3,'_cells_at_risk.png'))
ggsave(path, units="in", width=8, height=6, dpi=300)

######
######
######

iso3 = 'KEN'

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3, 'landslide', 'cells')
setwd(data_directory)

cells <- read.csv('assets_by_risk_cat.csv', header = T, sep = ",")
cells$asset_type = 'cells'
cells$perc = round((cells$count / sum(cells$count))*100,1)
cells = select(cells, risk_cat, asset_type, perc)

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3, 'landslide', 'fiber')
setwd(data_directory)

fiber <- read.csv('assets_by_risk_cat.csv', header = T, sep = ",")
fiber$asset_type = 'fiber'
fiber$perc = round((fiber$length_m / sum(fiber$length_m))*100,1)
fiber = select(fiber, risk_cat, asset_type, perc)

data = rbind(cells, fiber)

rm(fiber, cells)

data$risk_cat = factor(data$risk_cat,
                       levels=c("no_risk","low_risk","medium_risk", 'high_risk'),
                       labels=c("No Risk","Low Risk","Medium Risk", 'High Risk')
)

data$asset_type = factor(data$asset_type,
                         levels=c("cells","fiber"),
                         labels=c("Mobile Cells","Fiber Network")
)

max_y_value = max(data$perc, na.rm = TRUE)

plot1 = ggplot(data, aes(x=risk_cat, y=perc, fill=risk_cat)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_text(aes(label = paste(round(perc,2),"%")), size = 1.8,
            position = position_dodge(1), vjust =-1, hjust =.4, angle = 0)+
  theme(legend.position = '',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "Estimated Landslide Exposure for Mobile Cells and Fiber Assets in Kenya",
       subtitle = "Reported by Landslide Risk Category.", 
       x = "Landslide Risk Category", y = "Proportion of Assets at Risk (%)") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(expand = c(0, 0), limits=c(0, max_y_value+(max_y_value/4))) +
  facet_grid(~asset_type)

path = file.path(folder, 'figures', iso3, 'KEN_landslide_risk_relative.png')
ggsave(path, units="in", width=8, height=4, dpi=300)

iso3 = 'KEN'

folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3, 'landslide', 'cells')
setwd(data_directory)

cells <- read.csv('assets_by_risk_cat.csv', header = T, sep = ",")
cells$asset_type = 'cells'
# cells$perc = round((cells$count / sum(cells$count))*100,1)
cells = select(cells, risk_cat, asset_type, count)

cells$risk_cat = factor(cells$risk_cat,
                        levels=c("no_risk","low_risk","medium_risk", 'high_risk'),
                        labels=c("No Risk","Low Risk","Medium Risk", 'High Risk')
)

max_y_value = max(cells$count, na.rm = TRUE)

plot2 = 
  ggplot(cells, aes(x=risk_cat, y=count, fill=risk_cat)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_text(aes(label = scales::comma(count)), size = 1.8,
            position = position_dodge(1), vjust =-1, hjust =.4, angle = 0) +
  theme(legend.position = '',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "(A) Mobile Cell Exposure in Kenya",
       subtitle = "Reported by Landslide Risk Category.", 
       x = "Landslide Risk Category", y = "Mobile Cells at Risk") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(labels = scales::comma, expand = c(0, 0), 
                     limits=c(0, max_y_value+(max_y_value/4))) 


folder = dirname(rstudioapi::getSourceEditorContext()$path)
data_directory = file.path(folder, '..', 'results', iso3, 'landslide', 'fiber')
setwd(data_directory)

fiber <- read.csv('assets_by_risk_cat.csv', header = T, sep = ",")
fiber$asset_type = 'fiber'
fiber$length_km = fiber$length_m / 1e3 
fiber = select(fiber, risk_cat, asset_type, length_km)

fiber$risk_cat = factor(fiber$risk_cat,
                        levels=c("no_risk","low_risk","medium_risk", 'high_risk'),
                        labels=c("No Risk","Low Risk","Medium Risk", 'High Risk')
)

max_y_value = max(fiber$length_km, na.rm = TRUE)

plot3 = 
  ggplot(fiber, aes(x=risk_cat, y=length_km, fill=risk_cat)) + 
  geom_bar(stat="identity", position = position_dodge()) +
  geom_text(aes(label = scales::comma(length_km)), size = 1.8,
            position = position_dodge(1), vjust =-1, hjust =.4, angle = 0) +
  theme(legend.position = '',
        axis.text.x = element_text(angle=45, hjust=1)) +
  labs(colour=NULL,
       title = "(B) Fiber Exposure in Kenya",
       subtitle = "Reported by Landslide Risk Category.", 
       x = "Landslide Risk Category", y = "Fiber Network at Risk (Km)") +
  theme(panel.spacing = unit(0.6, "lines")) + 
  expand_limits(y=0) +
  guides(fill=guide_legend(ncol=3, title='Scenario')) +
  scale_fill_viridis_d(direction=1) +
  scale_x_discrete(expand = c(0, 0.15)) +
  scale_y_continuous(labels = scales::comma, expand = c(0, 0), 
                     limits=c(0, max_y_value+(max_y_value/4))) 

panel = ggarrange(
  plot2, 
  plot3, 
  # labels = c("A", "B"),
  # common.legend = TRUE,
  # legend = 'bottom',
  ncol = 2, nrow = 1)


path = file.path(folder, 'figures', iso3, 'KEN_landslide_risk_absolute.png')
ggsave(path, units="in", width=8, height=4, dpi=300)



