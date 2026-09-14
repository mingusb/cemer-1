package main
import("bufio";"fmt";"math";"os";"testing";"cogentcore.org/core/math32";"github.com/emer/leabra/v2/nxx1")
func TestPinnedActivationOracle(t *testing.T){
 path:=os.Getenv("NECKER_KERNEL_ORACLE");if path=="" {t.Fatal("NECKER_KERNEL_ORACLE required")};file,err:=os.Create(path);if err!=nil {t.Fatal(err)};defer file.Close();out:=bufio.NewWriter(file);defer out.Flush();p:=nxx1.Params{};p.Defaults()
 for i:=-88000;i<=50000;i++ {x:=float32(i)/1000;fmt.Fprintln(out,"E",math.Float32bits(x),math.Float32bits(math32.FastExp(x)))}
 for i:=-20000;i<=100000;i++ {x:=float32(i)/100000;fmt.Fprintln(out,"A",math.Float32bits(x),math.Float32bits(p.NoisyXX1(x)))}
 for _,x:=range []float32{-50/p.SigGainNVar,math.Nextafter32(-50/p.SigGainNVar,float32(math.Inf(-1))),math.Nextafter32(-50/p.SigGainNVar,float32(math.Inf(1))),0,p.InterpRange,math.Nextafter32(p.InterpRange,0)} {fmt.Fprintln(out,"A",math.Float32bits(x),math.Float32bits(p.NoisyXX1(x)))}
 t.Log("wrote258008 exact float32 oracle samples from unchanged pinned functions")
}
