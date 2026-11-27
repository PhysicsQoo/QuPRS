/* Research-only directed-rounding bound on a serialized complex phase weight.
 * Exact rational cycles in [0,1), exact rational radians; decimal weight.
 * MPFR intervals at 256 bits and sin/cos 1-Lipschitz on the real line.
 * Returns an upward-rounded binary64 bound on complex L1 error.
 */
#include <mpfr.h>
#include <gmp.h>
#include <math.h>
static int ratio(mpfr_t lo, mpfr_t hi, const char *s) {
    mpq_t q; mpq_init(q);
    int rc=mpq_set_str(q,s,10);
    if (!rc && mpz_sgn(mpq_denref(q))!=0) {
        mpq_canonicalize(q);
        mpfr_set_q(lo,q,MPFR_RNDD); mpfr_set_q(hi,q,MPFR_RNDU);
    } else rc=-1;
    mpq_clear(q); return rc;
}
double phase_error(const char *cycles,const char *rad,const char *re,const char *im) {
    mpfr_t a,b,c,d,p,q,l,h,width,x,y,u,v,t,s;
    mpfr_inits2(256,a,b,c,d,p,q,l,h,width,x,y,u,v,t,s,(mpfr_ptr)0);
    double answer=INFINITY;
    if (ratio(a,b,cycles)||ratio(c,d,rad)||mpfr_sgn(a)<0||mpfr_cmp_ui(b,1)>0) goto done;
    mpfr_const_pi(p,MPFR_RNDD); mpfr_const_pi(q,MPFR_RNDU);
    mpfr_mul(l,a,p,MPFR_RNDD); mpfr_add(l,l,c,MPFR_RNDD); mpfr_mul_ui(l,l,2,MPFR_RNDD);
    mpfr_mul(h,b,q,MPFR_RNDU); mpfr_add(h,h,d,MPFR_RNDU); mpfr_mul_ui(h,h,2,MPFR_RNDU);
    if (!mpfr_number_p(l)||!mpfr_number_p(h)||mpfr_cmp(l,h)>0) goto done;
    mpfr_sub(width,h,l,MPFR_RNDU);
    mpfr_set_zero(s,1);
    for (int i=0;i<2;i++) {
        const char *val=i?im:re;
        if (mpfr_set_str(u,val,10,MPFR_RNDD)||mpfr_set_str(v,val,10,MPFR_RNDU)) goto done;
        if (!mpfr_number_p(u)||!mpfr_number_p(v)) goto done;
        if (i) {mpfr_sin(x,l,MPFR_RNDD);mpfr_sin(y,l,MPFR_RNDU);}
        else {mpfr_cos(x,l,MPFR_RNDD);mpfr_cos(y,l,MPFR_RNDU);}
        mpfr_sub(t,v,x,MPFR_RNDU);mpfr_sub(a,y,u,MPFR_RNDU);
        if (mpfr_cmp(a,t)>0) mpfr_set(t,a,MPFR_RNDU);
        mpfr_add(t,t,width,MPFR_RNDU);
        if (mpfr_sgn(t)<0) goto done;
        mpfr_add(s,s,t,MPFR_RNDU);
    }
    answer=mpfr_get_d(s,MPFR_RNDU);
done:
    mpfr_clears(a,b,c,d,p,q,l,h,width,x,y,u,v,t,s,(mpfr_ptr)0);
    return answer;
}
