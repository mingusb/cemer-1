package main

import (
 "encoding/json"
 "math"
 "os"
 "path/filepath"
 "testing"
 "github.com/emer/emergent/v2/etime"
)

type PrecisionTrial struct {
 Trial int
 MaxActivationDifference float32
 MaxChannelDifference float32
 FirstCycleOver01 int
 ReferenceTransitions, ProbeTransitions [][2]int
}

func TestNeckerPrecisionSensitivity(t *testing.T) {
 directory:=os.Getenv("NECKER_PRECISION_OUTPUT");if directory=="" {t.Fatal("NECKER_PRECISION_OUTPUT required")};if err:=os.MkdirAll(directory,0755);err!=nil {t.Fatal(err)}
 bytes,err:=os.ReadFile(filepath.Join(os.Getenv("NECKER_REFERENCE_OUTPUT"),"authored-adaptation.json"));if err!=nil {t.Fatal(err)}
 var reference struct{Rows []ReferenceRow};if err=json.Unmarshal(bytes,&reference);err!=nil {t.Fatal(err)}
 for _,mode:=range []string{"exact-repeat","one-ulp-one-channel-once","one-ulp-all-channels-once","one-ulp-all-channels-every-trial"} {
  t.Run(mode,func(t *testing.T){
   sim:=&Sim{};sim.New();sim.ConfigAll();sim.Noise=.01;sim.KNaAdapt=true;sim.Cycles=1000
   for _,stack:=range sim.Loops.Stacks {removeGUI(&stack.OnInit);for _,loop:=range stack.Loops {removeGUI(&loop.OnStart);removeGUI(&loop.OnEnd)}}
   sim.Init();trials:=make([]PrecisionTrial,100);previousReference:=0;previousProbe:=0;exactNoise:=true;count:=0
   sim.Loops.Loop(etime.Test,etime.Cycle).OnEnd.Add("PrecisionObserver",func(){
    trial:=sim.Loops.Loop(etime.Test,etime.Trial).Counter.Cur;cycle:=sim.Context.Cycle;row:=reference.Rows[count];count++
    item:=&trials[trial];item.Trial=trial;if cycle==1 {previousReference=0;previousProbe=0}
    var referenceDelta,probeDelta float32
    for i,n:=range sim.Net.Layers[0].Neurons {
     d:=float32(math.Abs(float64(n.Act-row.Act[i])));if d>item.MaxActivationDifference {item.MaxActivationDifference=d};if d>.01 && item.FirstCycleOver01==0 {item.FirstCycleOver01=cycle}
     for j,value:=range []float32{n.GknaFast,n.GknaMed,n.GknaSlow} {expect:=[]float32{row.KFast[i],row.KMed[i],row.KSlow[i]}[j];delta:=float32(math.Abs(float64(value-expect)));if delta>item.MaxChannelDifference {item.MaxChannelDifference=delta}}
     if n.Noise!=row.Noise[i] {exactNoise=false};sign:=float32(1);if i>=8 {sign=-1};referenceDelta+=sign*row.Act[i]/8;probeDelta+=sign*n.Act/8
    }
    winner:=func(d float32)int {if d>.5 {return 1};if d < -.5 {return -1};return 0}
    rs,ps:=winner(referenceDelta),winner(probeDelta);if rs!=0 && rs!=previousReference {item.ReferenceTransitions=append(item.ReferenceTransitions,[2]int{cycle,rs});previousReference=rs};if ps!=0 && ps!=previousProbe {item.ProbeTransitions=append(item.ProbeTransitions,[2]int{cycle,ps});previousProbe=ps}
    // A controlled numerical perturbation of state, never a production model change.
    // It occurs after this trial's observed last cycle and before the next AlphaCycInit.
    if cycle==1000 && trial<99 && (trial==0 || mode=="one-ulp-all-channels-every-trial") {
     next:=func(x float32)float32{return math.Float32frombits(math.Float32bits(x)+1)}
     if mode=="one-ulp-one-channel-once" {n:=&sim.Net.Layers[0].Neurons[0];n.GknaFast=next(n.GknaFast)}
     if mode=="one-ulp-all-channels-once" || mode=="one-ulp-all-channels-every-trial" {for i:=range sim.Net.Layers[0].Neurons {n:=&sim.Net.Layers[0].Neurons[i];n.GknaFast=next(n.GknaFast);n.GknaMed=next(n.GknaMed);n.GknaSlow=next(n.GknaSlow)}}
    }
   })
   sim.Loops.ResetAndRun(etime.Test);if count!=100000 || !exactNoise {t.Fatalf("invalid paired probe cycles=%d exactNoise=%v",count,exactNoise)}
   if mode=="exact-repeat" {for _,trial:=range trials {if trial.MaxActivationDifference!=0 || trial.MaxChannelDifference!=0 {t.Fatal("untouched reference repeat is not exact")}}}
   output:=struct{Mode string;TotalCycles int;ExactNoise bool;Trials []PrecisionTrial}{mode,count,exactNoise,trials};b,err:=json.MarshalIndent(output,"","  ");if err!=nil {t.Fatal(err)};if err=os.WriteFile(filepath.Join(directory,mode+".json"),b,0644);err!=nil {t.Fatal(err)}
   maximum:=float32(0);for _,trial:=range trials {if trial.MaxActivationDifference>maximum {maximum=trial.MaxActivationDifference}};t.Logf("cycles%d exactNoise%v maxActDifference%g",count,exactNoise,maximum)
  })
 }
}
